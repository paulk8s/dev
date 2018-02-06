"""Generating CloudFormation template."""
from troposphere import (
    Base64,
    ec2,
    GetAtt,
    Join,
    Select,
    Output,
    Parameter,
    Ref,
    Template,
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

from awacs.sts import AssumeRole

ApplicationName = "jenkins"
ApplicationPort = "80"

t = Template()

t.add_description("Jenkins Server")

t.add_parameter(Parameter(
    "KeyPair",
    Description="Name of an existing EC2 KeyPair to SSH",
    Type="AWS::EC2::KeyPair::KeyName",
    ConstraintDescription="must be the name of an existing EC2 KeyPair.",
))

t.add_parameter(Parameter(
    "VpcId",
    Type="AWS::EC2::VPC::Id",
    Description="VPC",
    ConstraintDescription="VPC"
))

t.add_parameter(Parameter(
    "PrivateSubnet",
    Description="PrivateSubnet",
    Type="List<AWS::EC2::Subnet::Id>",
    ConstraintDescription="PrivateSubnet",
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
    GroupDescription="Allow TCP/80/22/443 access",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="8080",
            ToPort="8080",
            CidrIp="10.10.0.0/16",
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            CidrIp="10.10.0.0/16",
        ),
    ],
    VpcId=Ref("VpcId"),
))

ud = Base64(Join('', [
    "#!/bin/bash\n",
    "yum -y update\n",
    "mkdir /app\n",
    "curl -C - -LR#OH 'Cookie: oraclelicense=accept-securebackup-cookie' -k 'http://download.oracle.com/otn-pub/java/jdk/9.0.4+11/c2514751926b4512b076cc82f959763f/jdk-9.0.4_linux-x64_bin.tar.gz'\n",
    "tar -xzvf jdk* -C /app/\n",
    "export JAVA_HOME=/app/jdk-9\n",
    "export PATH=$PATH:$JAVA_HOME/bin\n",
    "source /etc/environment\n",
    "wget https://raw.githubusercontent.com/russest3/dev/master/java/java.csh\n",
    "wget https://raw.githubusercontent.com/russest3/dev/master/java/java.sh\n",
    "cp java.* /etc/profile.d/ && chmod 755 /etc/profile.d/java.*\n",
    "wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo && rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key\n",
    "yum -y install jenkins\n",
    "rm -f rm -f /usr/bin/java\n",
    "ln -s /app/jdk-9.0.4/bin/java /usr/bin/java\n",
    "sed -i 's/\/etc\/alternatives\/java/\/usr\/bin\/java/g' /etc/init.d/jenkins\n",
    "sed -i 's/\/usr\/lib\/jvm\/java-1.8.0\/bin\/java//g' /etc/init.d/jenkins\n",
    "sed -i 's/\/usr\/lib\/jvm\/jre-1.8.0\/bin\/java//g' /etc/init.d/jenkins\n",
    "sed -i 's/\/usr\/lib\/jvm\/java-1.7.0\/bin\/java//g' /etc/init.d/jenkins\n",
    "sed -i 's/\/usr\/lib\/jvm\/jre-1.7.0\/bin\/java//g' /etc/init.d/jenkins\n",
    "service jenkins start\n",
    "chkconfig jenkins on\n",
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
    PolicyName="AllowS3",
    PolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[Action("s3", "*")],
                Resource=["*"])
        ]
    ),
    Roles=[Ref("Role")]
))

t.add_resource(ec2.Instance(
    "server",
    ImageId="ami-97785bed",
    UserData=ud,
    InstanceType="t2.micro",
    KeyName=Ref("KeyPair"),
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            GroupSet=[Ref("SecurityGroup")],
            AssociatePublicIpAddress='false',
            SubnetId=Select("0", Ref("PrivateSubnet")),
            DeviceIndex='0',
        )]
))

print t.to_json()
