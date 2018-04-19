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
    "curl http://10.0.1.20:8081/artifactory/thirdparty/jdk-8u161-linux-x64.rpm -u admin:password --output jdk-8u161-linux-x64.rpm\n",
    "yum -y localinstall jdk-8u161-linux-x64.rpm\n",
    "/usr/sbin/alternatives --install /usr/bin/java java /usr/java/jdk1.8.0_11/bin/java 20000\n",
    "/usr/sbin/alternatives --set java /usr/java/jdk1.8.0_161/jre/bin/java\n",
    "curl --output /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat/jenkins.repo\n",
    "rpm --import https://pkg.jenkins.io/redhat/jenkins.io.key\n",
    "yum -y install jenkins python-simplejson\n",
    "service jenkins stop\n",    
    "yum -y remove java-1.7.0-openjdk.x86_64\n",
    "curl https://repos.fedorapeople.org/repos/dchen/apache-maven/epel-apache-maven.repo --output /etc/yum.repos.d/epel-apache-maven.repo\n",    
    "yum install -y apache-maven\n",    
    "service jenkins start\n",
    "chkconfig jenkins on\n",    
    "yum -y install ansible\n",
    "yum -y install git python-lxml\n",
    "pip install lxml\n",
    "chmod 0600 /var/lib/jenkins/.ssh/id_rsa*\n",
    "yum -y install docker\n",
    "service docker start\n",
    "chkconfig docker on\n",
    "usermod -a -G root jenkins\n",
    "curl --output /usr/local/bin/dcos https://downloads.dcos.io/binaries/cli/linux/x86-64/dcos-1.8/dcos\n",
    "chmod +x /usr/local/bin/dcos\n",
    "dcos config set core.dcos_url http://10.10.0.6\n"
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
