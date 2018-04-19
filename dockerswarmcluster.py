"""Generating CloudFormation template."""
from troposphere import (
    Base64,
    ec2,
    GetAtt,
    Join,
    Output,
    Parameter,
    Ref,
    Template,
    Select,
    elasticloadbalancing as elb,
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

t = Template()

t.add_description("Docker Swarm Cluster")

t.add_parameter(Parameter(
    "KeyPair",
    Description="Name of an existing EC2 KeyPair to SSH",
    Type="AWS::EC2::KeyPair::KeyName",
    ConstraintDescription="must be the name of an existing EC2 KeyPair.",
))

t.add_parameter(Parameter(
    "VpcId",
    Type="AWS::EC2::VPC::Id",
    Description="VPC"
))

t.add_parameter(Parameter(
    "Subnet",
    Description="Subnet",
    Type="List<AWS::EC2::Subnet::Id>",
    ConstraintDescription="Subnet"
))

t.add_parameter(Parameter(
    "Eth0",
    Type="AWS::EC2::NetworkInterface"
    GroupSet=[Ref("SecurityGroup")],
    
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

t.add_resource(ec2.SecurityGroup(
    "SecurityGroup",
    GroupDescription="Allow access from vpnserver",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="-1",
            FromPort="-1",
            ToPort="-1",
            SourceSecurityGroupId="sg-8da0dbfa",
        ),
    ],
    VpcId=Ref("VpcId"),
))

ud = Base64(Join('', [
    "#!/bin/bash\n",
    "yum -y install epel-release\n",
    "yum -y install python-pip\n",
    "pip install pystache\n",
    "pip install argparse\n",
    "pip install python-daemon\n",
    "pip install requests\n",
    "yum -y update\n",
    "cd /opt\n",
    "curl -O https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz\n",
    "tar -xvpf aws-cfn-bootstrap-latest.tar.gz\n",
    "cd aws-cfn-bootstrap-1.4/\n",
    "python setup.py build\n",
    "python setup.py install\n",
    "ln -s /usr/init/redhat/cfn-hup /etc/init.d/cfn-hup\n",
    "chmod 775 /usr/init/redhat/cfn-hup\n",
    "cd /opt\n",
    "mkdir aws\n",
    "cd aws\n",
    "mkdir bin\n",
    "ln -s /usr/bin/cfn-hup /opt/aws/bin/cfn-hup\n",
    "yum install -y yum-utils device-mapper-persistent-data lvm2\n",
    "yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo\n",
    "yum -y install docker-ce\n",
    "systemctl start docker\n",
    "systemctl enable docker\n",
]))

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

t.add_resource(IAMPolicy(
    "Policy",
    PolicyName="AllowEC2",
    PolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[Action("ec2", "*")],
                Resource=["*"]),
            Statement(
                Effect=Allow,
                Action=[Action("logs", "*")],
                Resource=["*"])
        ]
    ),
    Roles=[Ref("Role")]
))

t.add_resource(ec2.Instance(
    "server",
    ImageId="ami-97785bed",
    InstanceType="t2.micro",
    KeyName=Ref("KeyPair"),
    PrimaryIPAddress='10.10.0.30',
    SubnetId=Select("0", Ref("Subnet")),
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
                        
        )]
))

print t.to_json()