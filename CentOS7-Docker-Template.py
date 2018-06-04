"""Generating CloudFormation template."""

from ipaddress import ip_network

from ipify import get_ip

from troposphere import (
    Base64,
    ec2,
    GetAtt,
    Join,
    Output,
    Parameter,
    Ref,
    Template,
    elasticloadbalancing as elb,
    Select,
)

from troposphere.iam import (
    InstanceProfile,
    PolicyType as IAMPolicy,
    Role,
)

from awacs.aws import (
    Action,
    Allow,
    Policy,
    Principal,
    Statement,
)

from troposphere.autoscaling import (
    AutoScalingGroup,
    LaunchConfiguration,
    ScalingPolicy,
)

from troposphere.cloudwatch import (
    Alarm,
    MetricDimension,
)

from awacs.sts import AssumeRole

ApplicationPort = "8080"
PublicCidrIp = str(ip_network(get_ip()))

t = Template()

t.add_description("CentOS7-Docker-Template")

t.add_parameter(Parameter(
    "KeyPair",
    Description="Name of an existing EC2KeyPair to SSH",
    Type="AWS::EC2::KeyPair::KeyName",
    ConstraintDescription="must be the name of an existing EC2KeyPair."
))

t.add_parameter(Parameter(
    "VpcId",
    Type="AWS::EC2::VPC::Id",
    Description="VPC"
))

t.add_parameter(Parameter(
    'InstanceType',
    Type='String',
    Description='WebServer EC2 instance type',
    Default='t2.micro',
    AllowedValues=[
        't2.micro',
        't2.small',
        't2.medium',
        't2.large',
    ],
    ConstraintDescription='must be a valid EC2 T2 instance type.',
))

t.add_parameter(Parameter(
    "SubnetID",
    Description="SubnetID",
    Type="List<AWS::EC2::Subnet::Id>",
    ConstraintDescription="SubnetID"
))

t.add_resource(ec2.SecurityGroup(
    "SGCentOS7DockerTemplate",
    GroupDescription="SG-CentOS7-Docker-Template",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=ApplicationPort,
            ToPort=ApplicationPort,
            CidrIp=PublicCidrIp,
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            CidrIp=PublicCidrIp,
        )
    ],
    VpcId=Ref("VpcId")
))

t.add_resource(Role(
    "Role",
    AssumeRolePolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[AssumeRole],
                Principal=Principal("Service", ["ec2.amazonaws.com"])
            )
        ]
    )
))

t.add_resource(InstanceProfile(
    "InstanceProfile",
    Path="/",
    Roles=[Ref("Role")]
))

ud = Base64(Join('', [
    "#!/bin/bash\n",
    "yum -y update && yum -y upgrade\n",
    "/usr/bin/easy_install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz 2>&1 >> /var/log/initial_user-data.log\n",
    "yum -y install epel-release\n",
    "yum -y install python-pip\n",
    "pip install --upgrade pip\n",
    "pip install docker-compose\n",
    "yum install -y yum-utils device-mapper-persistent-data lvm2\n",
    "yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo\n",
    "yum -y install docker-ce\n",
    "systemctl start docker\n",
    "systemctl enable docker\n",
    "yum -y install git\n",
]))

t.add_resource(ec2.Instance(
    "server",
    ImageId="ami-4bf3d731",
    InstanceType=Ref("InstanceType"),
    UserData=ud,
    KeyName=Ref("KeyPair"),
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            GroupSet=[Ref("SGCentOS7DockerTemplate")],
            AssociatePublicIpAddress='true',
            SubnetId=Select("0", Ref("SubnetID")),
            DeviceIndex='0',
        )]
))

print t.to_json()
