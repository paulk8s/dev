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

ApplicationPort = "8100"

t = Template()

t.add_description("CloudFormation Template - AppServers")

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
    GroupDescription="AppServers Security Group",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            CidrIp="10.10.93.149/32",
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
            "TCP:",
            ApplicationPort
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
    "IP=$(hostname -I)\n",
    "sed -i s/127.0.0.1/$IP/g /app/wildfly-11.0.0.Final/standalone/configuration/standalone.xml\n",
    "/app/wildfly-11.0.0.Final/bin/standalone.sh &\n"
]))

t.add_resource(Role(
    "AppServersRole",
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
    "AppServersInstanceProfile",
    Path="/",
    Roles=[Ref("AppServersRole")]
))

t.add_resource(IAMPolicy(
    "Policy",
    PolicyName="AllowS3",
    PolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[Action("s3", "*")],
                Resource=["*"]),
            Statement(
                Effect=Allow,
                Action=[Action("logs", "*")],
                Resource=["*"])
        ]
    ),
    Roles=[Ref("AppServersRole")]
))

t.add_resource(LaunchConfiguration(
    "LaunchConfiguration",
    UserData=ud,
    ImageId="ami-eaa5bf90",
    KeyName=Ref("KeyPair"),
    SecurityGroups=[Ref("SecurityGroup")],
    InstanceType=Ref("InstanceType"),
    IamInstanceProfile=Ref("AppServersInstanceProfile"),
))

t.add_resource(AutoScalingGroup(
    "AutoscalingGroup",
    DesiredCapacity=Ref("ScaleCapacity"),
    LaunchConfigurationName=Ref("LaunchConfiguration"),
    MinSize=1,
    MaxSize=1,
    LoadBalancerNames=[Ref("LoadBalancer")],
    VPCZoneIdentifier=Ref("PublicSubnet"),
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
