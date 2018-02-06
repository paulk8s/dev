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

ApplicationName = "nodeserver"
ApplicationPort = "3000"

#GithubAccount = "russest3"
#GithubAnsibleURL = "https://github.com/{}/ansible".format(GithubAccount)

#AnsiblePullCmd = \
#    "/usr/local/bin/ansible-pull -U {} {}.yml -i localhost".format(
#        GithubAnsibleURL,
#        ApplicationName
#    )

t = Template()

t.add_description("Effective DevOps in AWS: HelloWorld web application")

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
    "PublicSubnet",
    Description="PublicSubnet",
    Type="List<AWS::EC2::Subnet::Id>",
    ConstraintDescription="PublicSubnet"
))

t.add_parameter(Parameter(
    "PrivateSubnet",
    Description="PrivateSubnet",
    Type="List<AWS::EC2::Subnet::Id>",
    ConstraintDescription="PrivateSubnet"
))

t.add_parameter(Parameter(
    "ScaleCapacity",
    Default="1",
    Type="String",
    Description="Number servers to run",
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
    GroupDescription="Allow SSH access".format(ApplicationPort),
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            CidrIp="10.10.0.0/16",
        ),        
    ],
    VpcId=Ref("VpcId"),
))

t.add_resource(ec2.SecurityGroup(
    "LoadBalancerSecurityGroup",
    GroupDescription="Web load balancer security group.",
    VpcId=Ref("VpcId"),
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="80",
            ToPort="80",
            CidrIp="0.0.0.0/0",
        ),
    ],
))

t.add_resource(elb.LoadBalancer(
    "LoadBalancer",
    Scheme="internet-facing",
    Listeners=[
        elb.Listener(
            LoadBalancerPort="80",
            InstancePort=ApplicationPort,
            Protocol="HTTP",
            InstanceProtocol="HTTP"
        ),
    ],
    HealthCheck=elb.HealthCheck(
        Target=Join("", [
			"HTTP:",
			ApplicationPort, "/"
    ]),
        HealthyThreshold="5",
        UnhealthyThreshold="2",
        Interval="20",
        Timeout="15",
    ),
    ConnectionDrainingPolicy=elb.ConnectionDrainingPolicy(
        Enabled=True,
        Timeout="10",
    ),
    CrossZone=True,
    Subnets=Ref("PublicSubnet"),
    SecurityGroups=[Ref("LoadBalancerSecurityGroup")],
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
    "wget http://download.jboss.org/wildfly/11.0.0.Final/wildfly-11.0.0.Final.zip\n",
    "unzip wildfly-11.0.0.Final.zip -d /app/\n",
    "echo JBOSS_HOME='/app/wildfly-11.0.0.Final' >> /app/wildfly-11.0.0.Final/bin/standalone.conf\n",
    "echo JAVA_HOME='/app/jdk-9.0.4' >> /app/wildfly-11.0.0.Final/bin/standalone.conf\n",
    "IP=$(ifconfig | grep 'inet addr' | grep -v 127.0.0.1 | cut -d ':' -f 2 | awk '{ print $1 }')\n",
    "sed -i s/127.0.0.1/$IP/g /app/wildfly-11.0.0.Final/standalone/configuration/standalone.xml\n",
    "/app/wildfly-11.0.0.Final/bin/standalone.sh &\n"
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

t.add_resource(LaunchConfiguration(
    "LaunchConfiguration",
    UserData=ud,
    ImageId="ami-97785bed",
    KeyName=Ref("KeyPair"),
    SecurityGroups=[Ref("SecurityGroup")],
    InstanceType=Ref("InstanceType"),
    IamInstanceProfile=Ref("InstanceProfile"),
))

t.add_resource(AutoScalingGroup(
    "AutoscalingGroup",
    DesiredCapacity=Ref("ScaleCapacity"),
    LaunchConfigurationName=Ref("LaunchConfiguration"),
    MinSize=1,
    MaxSize=1,
    LoadBalancerNames=[Ref("LoadBalancer")],
    VPCZoneIdentifier=Ref("PrivateSubnet"),
))

t.add_resource(ScalingPolicy(
    "ScaleDownPolicy",
    ScalingAdjustment="-1",
    AutoScalingGroupName=Ref("AutoscalingGroup"),
    AdjustmentType="ChangeInCapacity",
))

t.add_resource(ScalingPolicy(
    "ScaleUpPolicy",
    ScalingAdjustment="1",
    AutoScalingGroupName=Ref("AutoscalingGroup"),
    AdjustmentType="ChangeInCapacity",
))

t.add_resource(Alarm(
    "CPUTooLow",
    AlarmDescription="Alarm if CPU too low",
    Namespace="AWS/EC2",
    MetricName="CPUUtilization",
    Dimensions=[
        MetricDimension(
            Name="AutoScalingGroupName",
            Value=Ref("AutoscalingGroup")
        ),
    ],
    Statistic="Average",
    Period="60",
    EvaluationPeriods="1",
    Threshold="30",
    ComparisonOperator="LessThanThreshold",
    AlarmActions=[Ref("ScaleDownPolicy")],
))

t.add_resource(Alarm(
    "CPUTooHigh",
    AlarmDescription="Alarm if CPU too high",
    Namespace="AWS/EC2",
    MetricName="CPUUtilization",
    Dimensions=[
        MetricDimension(
            Name="AutoScalingGroupName",
            Value=Ref("AutoscalingGroup")
        ),
    ],
    Statistic="Average",
    Period="60",
    EvaluationPeriods="1",
    Threshold="60",
    ComparisonOperator="GreaterThanThreshold",
    AlarmActions=[Ref("ScaleUpPolicy"), ],
    InsufficientDataActions=[Ref("ScaleUpPolicy")],
))

t.add_output(Output(
    "WebUrl",
    Description="Application endpoint",
    Value=Join("", [
        "http://", GetAtt("LoadBalancer", "DNSName"),
        ":", ApplicationPort
    ]),
))

print t.to_json()
