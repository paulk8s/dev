#!/usr/local/bin/ksh93

set +o nounset
if [ "x${DEBUG}" = "x" ]; then
# Set DEBUG="yes" here or as an environment variable to enable set -x in all functions
DEBUG="no"; export DEBUG
fi

function usage {
echo "${my_name} [-bcefhmps] <Component> <Version> <Environment>"
echo 
echo "-b	Do not perform DB backup before DB upgrade"
echo "-c	Generate and deploy config files only"
echo "-e	Do not perform config encryption"
echo "-f	Force the deployment (ignore locking and version check)"
echo "-h	This small usage guide"
echo "-m	Do not email the deployment notification"
echo "-p	Preparation mode; generate the configs and copy the packages to target servers and exit"
echo "-s	Parameters sanity check; check is Component and Version are valid then exit"
}


### Main

#set -x
set -o nounset

my_name=$0
OPERATION_NAME="Main"; export OPERATION_NAME

if [ $# -lt 3 ]; then 
	usage
	exit 1
fi

#set -x

FLAG_B_IS_SET="no"
FLAG_C_IS_SET="no"
FLAG_E_IS_SET="no"
FLAG_F_IS_SET="no"
FLAG_M_IS_SET="no"
FLAG_P_IS_SET="no"
FLAG_S_IS_SET="no"

args=`getopt bcefpsmh: $*`
if [ $? != 0 ]
then
        usage
	exit 1
fi
set -- $args
for i
do
        case "$i"
        in
                -b)
                        FLAG_B_IS_SET="yes"
                        shift
			;;
                -c)
                        FLAG_C_IS_SET="yes"
                        shift
			;;
		-e)
                        FLAG_E_IS_SET="yes"
                        shift
			;;
		-f)
                        FLAG_F_IS_SET="yes"
                        shift
			;;
		-m)
                        FLAG_M_IS_SET="yes"
                        shift
			;;
		-p)
                        FLAG_P_IS_SET="yes"
                        shift
			;;
		-s)
                        FLAG_S_IS_SET="yes"
                        shift
			;;
		-h)
                        usage
			exit 0
			;;
                --)
                        shift; break
			;;
        esac
done


COMPONENT=$1; export COMPONENT
if [ "x${COMPONENT}" = "x" ]; then
	usage
	exit 1
fi

VERSION=$2; export VERSION
if [ "x${VERSION}" = "x" ]; then
	usage
	exit 1
fi

ENVIRONMENT=$3;
if [ "x${ENVIRONMENT}" = "x" ]; then
	usage
	exit 1
fi
ENVIRONMENT=`echo ${ENVIRONMENT} | tr "[:lower:]" "[:upper:]"`; export ENVIRONMENT

DEPLOYMENT_ID=$$; export DEPLOYMENT_ID

# We do not have L_BASE_DIR variable set at this stage; so let's try to figure out the absolute path to deploy.ksh (this script) 
# and run local.ksh from the same directory
MY_NAME=$0
if [ `echo ${MY_NAME} | cut -c1` = "/" ]; then # Absolute path
MY_FULL_PATH="${MY_NAME}"
else
MY_CWD=`pwd`
MY_FULL_PATH="${MY_CWD}/${MY_NAME}"
fi
MY_DIR=`dirname ${MY_FULL_PATH}`

L_LOCAL_SETTINGS_FILE="${MY_DIR}/local.ksh"

if [ -e ${L_LOCAL_SETTINGS_FILE} ] ; then
	.  ${L_LOCAL_SETTINGS_FILE}
else
	log "Error: Local settings file does not exist: ${L_LOCAL_SETTINGS_FILE}"
	exit 1
fi
# From this point we have local varibales defined


#L_DEPLOY_COMPONENT_FILE=${L_BASE_DIR}/Components/${COMPONENT}
#L_DEPLOY_COMMON_COMPONENT_FILE=${L_BASE_DIR}/Components/common
#L_DEPLOY_OPS_FILE=${L_BASE_DIR}/deployment_operations.ksh
#L_CUSTOM_DEPLOY_SCRIPT="${L_BASE_DIR}/custom_deploy.ksh"


if [ -e ${L_DEPLOY_OPS_FILE} ] ; then
	.  ${L_DEPLOY_OPS_FILE}
else
	echo "Error: Deployment operations file does not exist: ${L_DEPLOY_OPS_FILE}"
	exit 1
fi
# From this point we have functions for basic deplyment operations defined

# Let's make sure we have either Component file or Environment file. We can not have both missing.
if [ ! -e ${L_DEPLOY_COMPONENT_FILE} -a ! -e ${L_DEPLOY_ENVIRONMENT_FILE} ]; then
	log "Do not know how to deploy ${COMPONENT} to environment ${ENVIRONMENT}"
	fail "Make sure that either Components/${COMPONENT} or Environments/${ENVIRONMENT} file exists"

fi


# Let's see what variables are set by L_DEPLOY_COMMON_COMPONENT_FILE and L_DEPLOY_COMPONENT_FILE

env > ${L_TEMP_DIR}/env_before_cmp.lst
if [ -e ${L_DEPLOY_COMMON_COMPONENT_FILE} ] ; then
	.  ${L_DEPLOY_COMMON_COMPONENT_FILE} 
fi

if [ -e ${L_DEPLOY_COMPONENT_FILE} ] ; then
	.  ${L_DEPLOY_COMPONENT_FILE} 
else
	log "WARNING: Component file for ${COMPONENT} not found; proceeding without it"
fi
env > ${L_TEMP_DIR}/env_after_cmp.lst

cat ${L_TEMP_DIR}/env_after_cmp.lst | while read v; do
	var1=`echo $v | cut -f1 -d\=`
	grep -q $var1 ${L_TEMP_DIR}/env_before_cmp.lst || echo $var1 
done >> ${L_TEMP_DIR}/env_cmp.lst

# Unset them for now
for v in `cat ${L_TEMP_DIR}/env_cmp.lst`; do
	eval unset $v
done

# Now let's see what variales are set by L_DEPLOY_COMMON_ENVIRONMENT_FILE and L_DEPLOY_ENVIRONMENT_FILE


env > ${L_TEMP_DIR}/env_before_envr.lst
if [ -e ${L_DEPLOY_COMMON_ENVIRONMENT_FILE} ] ; then
	.  ${L_DEPLOY_COMMON_ENVIRONMENT_FILE} 
fi

if [ -e ${L_DEPLOY_ENVIRONMENT_FILE} ] ; then
	.  ${L_DEPLOY_ENVIRONMENT_FILE} 
#else
#	log "WARNING: Environment file for ${ENVIRONMENT} not found; proceeding without it"
fi

env > ${L_TEMP_DIR}/env_after_envr.lst

cat ${L_TEMP_DIR}/env_after_envr.lst | while read v; do
	var1=`echo $v | cut -f1 -d\=`
	grep -q $var1 ${L_TEMP_DIR}/env_before_envr.lst || echo $var1 
done >> ${L_TEMP_DIR}/env_envr.lst

#cat ${L_TEMP_DIR}/env_envr.lst

# Unset them for now
for v in `cat ${L_TEMP_DIR}/env_envr.lst`; do
	eval unset $v
done

# Determine the overlapping varibales

cat ${L_TEMP_DIR}/env_cmp.lst | while read v; do
	grep -q $v ${L_TEMP_DIR}/env_envr.lst && echo $v
done >> ${L_TEMP_DIR}/overlap.lst

if [ -s ${L_TEMP_DIR}/overlap.lst ]; then
	log "Found overlaping variables."
	log "The following variables are set in both Components/${COMPONENT} and Environments/${ENVIRONMENT} scripts:"
	cat ${L_TEMP_DIR}/overlap.lst
	fail "Set the variables only in one place."
fi

########### All is good, no overlaps found; we can read the varaibles for real now.#############
if [ -e ${L_DEPLOY_COMMON_COMPONENT_FILE} ] ; then
	.  ${L_DEPLOY_COMMON_COMPONENT_FILE} 2>&1 > /dev/null
fi

if [ -e ${L_DEPLOY_COMPONENT_FILE} ] ; then
	.  ${L_DEPLOY_COMPONENT_FILE} 2>&1 > /dev/null
fi

if [ -e ${L_DEPLOY_COMMON_ENVIRONMENT_FILE} ] ; then
	.  ${L_DEPLOY_COMMON_ENVIRONMENT_FILE} 2>&1 > /dev/null
fi

if [ -e ${L_DEPLOY_ENVIRONMENT_FILE} ] ; then
	.  ${L_DEPLOY_ENVIRONMENT_FILE} 2>&1 > /dev/null
fi

########### From this point we have Environment specific varibales defined #############


if [ $REQUIRE_CONFIRMATION != "no" ]; then
	if [ ${FLAG_F_IS_SET} != "yes" ]; then
		echo "=============================================="
		echo "WARNING: this deployment requires confirmation"
		echo "=============================================="
		ask_confirmation "Do you really want to proceed with the deployment? (yes/no) "
		RC=$?
		if [ $RC -eq 0 ]; then # answered no; exiting
			exit 2
		fi
		echo
	else
		log "The deployment is running with -f option; ignoring REQUIRE_CONFIRMATION value"
	fi
fi


if [ ${FLAG_F_IS_SET} != "yes" ]; then
	# Get the latest version of COMPONENT deployed in ENVIRONMENT from L_LOG_FILE2 log file
	if [ -e ${L_LOG_FILE2} ]; then
		LAST_VERSION=`grep '|'"${COMPONENT} " ${L_LOG_FILE2} | grep " ${ENVIRONMENT}"'|SUCCESS' | grep -v CONFIGONLY | tail -1 | cut -d\| -f4 | cut -d' ' -f2`
	else
		LAST_VERSION=""
	fi
	# If this is the first time deployment set last_version to 0.0.0.0 to trick the deployment script
	if [ "x${LAST_VERSION}" = "x" ]; then
	LAST_VERSION="0.0.0.0"
	fi
	#set -x
	# Split VERSION and LAST_VERSION into 4 parts (expected format: a.b.c.d)
	VERSION_PART1=`IFS='.'; set ${VERSION}; echo $1`
	if [ "x${VERSION_PART1}" = "x" ]; then
		echo "Unexpected version format"
		echo "Requested version: ${VERSION}"
		echo "Last deployed version: ${LAST_VERSION}"
		exit 3
	fi
	VERSION_PART2=`IFS='.'; set ${VERSION}; echo $2`
	if [ "x${VERSION_PART2}" = "x" ]; then
		echo "Unexpected version format"
		echo "Requested version: ${VERSION}"
		echo "Last deployed version: ${LAST_VERSION}"
		exit 3
	fi
	VERSION_PART3=`IFS='.'; set ${VERSION}; echo $3`
	if [ "x${VERSION_PART3}" = "x" ]; then
		echo "Unexpected version format"
		echo "Requested version: ${VERSION}"
		echo "Last deployed version: ${LAST_VERSION}"
		exit 3
	fi
	VERSION_PART4=`IFS='.'; set ${VERSION}; echo $4`
	if [ "x${VERSION_PART4}" = "x" ]; then
		echo "Unexpected version format"
		echo "Requested version: ${VERSION}"
		echo "Last deployed version: ${LAST_VERSION}"
		exit 3
	fi

	LAST_VERSION_PART1=`IFS='.'; set ${LAST_VERSION}; echo $1`
	LAST_VERSION_PART2=`IFS='.'; set ${LAST_VERSION}; echo $2`
	LAST_VERSION_PART3=`IFS='.'; set ${LAST_VERSION}; echo $3`
	LAST_VERSION_PART4=`IFS='.'; set ${LAST_VERSION}; echo $4`

	if [ "x${LAST_VERSION}" = "x0.0.0.0" ]; then
	LAST_VERSION="Unknown"
	fi

	# Let's make sure the parts are actually the numbers

	expr ${VERSION_PART1} + ${VERSION_PART2} + ${VERSION_PART3} + ${VERSION_PART4} + ${LAST_VERSION_PART1} + ${LAST_VERSION_PART2} + ${LAST_VERSION_PART3} + ${LAST_VERSION_PART4} > /dev/null 2>&1
	if [ $? -ne 0 ]; then # Something wrong some of the parts are not the numbers; exit
		echo "Unexpected version format"
		echo "Requested version: ${VERSION}"
		echo "Last deployed version: ${LAST_VERSION}"
		exit 3
	fi

	# Compare the parts
	NEED_CONFIRMATION="no"

	if [ ${FLAG_S_IS_SET} != "yes" ]; then
		if [ ${VERSION_PART1} -eq ${LAST_VERSION_PART1} -a ${VERSION_PART2} -eq ${LAST_VERSION_PART2} -a ${VERSION_PART3} -eq ${LAST_VERSION_PART3} -a ${VERSION_PART4} -eq ${LAST_VERSION_PART4} ]; then
			echo "You are trying to deploy ${COMPONENT} ${VERSION} to ${ENVIRONMENT}"
			echo "But it looks like the same version was already deployed earlier"
			echo
			NEED_CONFIRMATION="yes"		 

		elif [ ${VERSION_PART1} -lt ${LAST_VERSION_PART1} ]; then
			echo "You are trying to deploy ${COMPONENT} ${VERSION} to ${ENVIRONMENT}"
			echo "But it looks like higher version ${LAST_VERSION} is already deployed"
			echo
			NEED_CONFIRMATION="yes"

		elif [ ${VERSION_PART1} -eq ${LAST_VERSION_PART1} -a ${VERSION_PART2} -lt ${LAST_VERSION_PART2} ]; then
			echo "You are trying to deploy ${COMPONENT} ${VERSION} to ${ENVIRONMENT}"
			echo "But it looks like higher version ${LAST_VERSION} is already deployed"
			echo
			NEED_CONFIRMATION="yes"

		elif [ ${VERSION_PART1} -eq ${LAST_VERSION_PART1} -a ${VERSION_PART2} -eq ${LAST_VERSION_PART2} -a ${VERSION_PART3} -lt ${LAST_VERSION_PART3} ]; then
			echo "You are trying to deploy ${COMPONENT} ${VERSION} to ${ENVIRONMENT}"
			echo "But it looks like higher version ${LAST_VERSION} is already deployed"
			echo
			NEED_CONFIRMATION="yes"


		elif [ ${VERSION_PART1} -eq ${LAST_VERSION_PART1} -a ${VERSION_PART2} -eq ${LAST_VERSION_PART2} -a ${VERSION_PART3} -eq ${LAST_VERSION_PART3} -a ${VERSION_PART4} -lt ${LAST_VERSION_PART4} ]; then
			echo "You are trying to deploy ${COMPONENT} ${VERSION} to ${ENVIRONMENT}"
			echo "But it looks like higher version ${LAST_VERSION} is already deployed"
			echo
			NEED_CONFIRMATION="yes"
		fi
	fi

	if [ $REQUIRE_CONSEQUTIVE_VERSIONS != "no" ]; then
		# Calculate difference
		VERSION_DIFF=`expr ${VERSION_PART4} - ${LAST_VERSION_PART4}`
		if [ $VERSION_DIFF -ne 1 ]; then
			echo "This deployment requires consecutive version"
			echo "Requested version: ${VERSION}"
			echo "Last deployed version: ${LAST_VERSION}"
			echo
			NEED_CONFIRMATION="yes"
		fi
	fi


	if [ ${NEED_CONFIRMATION} = "yes" -a ${FLAG_S_IS_SET} != "yes" ]; then
		ask_confirmation "Proceed anyway? (yes/no) "
		RC=$?
		if [ $RC -eq 0 ]; then # answered no; exiting
			exit 2
		fi
	fi
else
	log "The deployment is running with -f option; skipping version check"
fi

if [ ${FLAG_S_IS_SET} = "yes" ]; then
	log "The deployment is running with -s option; Sanity check passed, exiting now"
	exit 0
fi

L_LOCK_IS_SET="no"
# Check for the lock
if [ -e ${L_LOCK_FILE} ]; then
	if [ ${FLAG_F_IS_SET} != "yes" ]; then
		echo "Unable to deploy ${COMPONENT} to ${ENVIRONMENT}" | tee -a ${L_LOG_FILE}
		echo "The lock file found. The conflicting deployment information is below" | tee -a ${L_LOG_FILE}
		echo "=======================" | tee -a ${L_LOG_FILE}
		cat ${L_LOCK_FILE} | tee -a ${L_LOG_FILE}
		echo "=======================" | tee -a ${L_LOG_FILE}
		L_LOCK_IS_SET="yes"
	else
		echo "The lock file found. The conflicting deployment information is below" | tee -a ${L_LOG_FILE}
		echo "=======================" | tee -a ${L_LOG_FILE}
		cat ${L_LOCK_FILE} | tee -a ${L_LOG_FILE}
		echo "=======================" | tee -a ${L_LOG_FILE}
		log "The deployment is running with -f option; ignoring the existing lock"
	fi
else

# Set the lock

echo "Deployment ID: ${DEPLOYMENT_ID}" > ${L_LOCK_FILE}
echo "Deployment request: ${COMPONENT} ${VERSION} ${ENVIRONMENT}" >> ${L_LOCK_FILE}
echo "User: ${L_CURRENT_USER}" >> ${L_LOCK_FILE}
echo "Timestamp: `date`" >> ${L_LOCK_FILE}


log "Starting deployment of ${COMPONENT} version ${VERSION} to ${ENVIRONMENT}" | tee -a ${L_LOG_FILE}
if [ ${FLAG_C_IS_SET} = "yes" ]; then
log "=================================" | tee -a ${L_LOG_FILE}
log "DEPLOYING CONFIGURATION FILE ONLY" | tee -a ${L_LOG_FILE}
log "=================================" | tee -a ${L_LOG_FILE}
fi
log "Deployment ID: ${DEPLOYMENT_ID}" | tee -a ${L_LOG_FILE}
log "Started by: ${L_CURRENT_USER} @ ${L_SERVER_NAME}" | tee -a ${L_LOG_FILE}
log "Log File: ${L_LOG_FILE}" | tee -a ${L_LOG_FILE}

#log "Starting deployment of ${COMPONENT} version ${VERSION} to ${ENVIRONMENT}" > ${L_LOG_FILE}
if [ ${FLAG_C_IS_SET} != "yes" ]; then
	#commented for GIT
	#p4_get_custom_deploy 2>&1 >>${L_LOG_FILE}
	get_custom_deploy 2>&1 >>${L_LOG_FILE}
else
# When running with -c option use custom_deploy_c.ksh
	L_CUSTOM_DEPLOY_SCRIPT=${L_BASE_DIR}/custom_deploy_c.ksh	
fi

chmod ug+w ${L_CUSTOM_DEPLOY_SCRIPT}


if [ "$ENABLE_SSH_SESSION_SHARING" = "yes" ]; then
# D_VERSION_SERVERS D_VERSION_SSH_USER
# D_QHDB_SERVERS D_QHDB_SSH_USER
# D_APP_SERVERS D_APP_SSH_USER
# D_APACHE_SERVERS D_APACHE_SSH_USER
(
	set +o nounset
	if [ "x${D_APP_SERVERS}" != "x" ]; then
		typeset -n TARGET_CREDENTIALS=D_APP_SSH_USER; export TARGET_CREDENTIALS
		typeset -n TARGET_SERVERS=D_APP_SERVERS; export TARGET_SERVERS
		establish_ssh_master_session
	fi
	if [ "x${D_QHDB_SERVERS}" != "x" ]; then
		typeset -n TARGET_CREDENTIALS=D_QHDB_SSH_USER; export TARGET_CREDENTIALS
		typeset -n TARGET_SERVERS=D_QHDB_SERVERS; export TARGET_SERVERS
		establish_ssh_master_session
	fi
	if [ "x${D_VERSION_SERVERS}" != "x" ]; then
		typeset -n TARGET_CREDENTIALS=D_VERSION_SSH_USER; export TARGET_CREDENTIALS
		typeset -n TARGET_SERVERS=D_VERSION_SERVERS; export TARGET_SERVERS
		establish_ssh_master_session
	fi
	if [ "x${D_APACHE_SERVERS}" != "x" ]; then
		typeset -n TARGET_CREDENTIALS=D_APACHE_SSH_USER; export TARGET_CREDENTIALS
		typeset -n TARGET_SERVERS=D_APACHE_SERVERS; export TARGET_SERVERS
		establish_ssh_master_session
	fi
	set -o nounset
# Establish master session to the release machine
	if [ -S "${L_SSH_CONTROL_DIR}/Build@release.dev.medfusion.net:22" ]; then
		log "SSH master session to release.dev.medfusion.net is aready esatblished"
	else
		log "Establishing SSH master session to release.dev.medfusion.net ..."
		${SSH_COMMAND} -l Build release.dev.medfusion.net -M -f "sleep 900" < /dev/null > /dev/null 2>&1
		RC=$?
		if [ ${RC} != 0 ]; then
			fail "failed"
		fi	
		log "success"
	fi
)
fi

log "Executing deployment script ${L_CUSTOM_DEPLOY_SCRIPT} for ${COMPONENT}"
#=========================================================================================== 
# Run custom deploy script 
if [ ${DEBUG} = "yes" ]; then
#=========================================================================================== 
# Run custom deploy script in debug mode

(
. ${L_CUSTOM_DEPLOY_SCRIPT}
)
#=========================================================================================== 
else
#=========================================================================================== 
# Run custom deploy script 

(
. ${L_CUSTOM_DEPLOY_SCRIPT} 
) | tee -a ${L_LOG_FILE}
#===========================================================================================
fi
fi # If lock is set

DEPLOYMENT_STATUS="UNKNOWN"

if [ ${L_LOCK_IS_SET} = "yes" ]; then
	MAIL_TO=${MAIL_TO_LOCKED}
	DEPLOYMENT_STATUS="LOCKED"
else
	grep -v usp_iam_Failed ${L_LOG_FILE} | grep -v SignUpFailure | grep -v pr_failed | grep -v pr_shoutout | grep -v IDENTITY.FAILED_AUTHENTICATION | grep -v update_db_version_failure.sql | grep -v usp_email_failures_rpt | grep -v "only warning if failed" | grep -v update_db_version_rollback_failure.sql | grep -q -i "fail"
	RC=$?
	if [ ${RC} -eq 0 ]; then
	log "Deployment failed"
	# Don't send to everyone if it failed: We only want to report successful ones =)
	MAIL_TO=${MAIL_TO_FAILED}
	DEPLOYMENT_STATUS="FAILED"
	else
	log "Deployment successful"
	MAIL_TO=${MAIL_TO_SUCCESS}
	DEPLOYMENT_STATUS="SUCCESS"
	fi
	#Remove lock
	rm -f ${L_LOCK_FILE}
fi 

# If successful run the GUI tests
if [ "${DEPLOYMENT_STATUS}" = "SUCCESS" ]; then
	if [ "${GUITESTS_ENABLE}" = "yes" ]; then
		${L_BASE_DIR}/deploy.ksh -fm ${GUITESTS_NAME} ${VERSION} ${ENVIRONMENT} | tee -a ${L_LOG_FILE}
	fi
fi

export GUITESTS_URL=`cat ${L_LOG_FILE} | grep ^GUITESTS_URL | cut -d" " -f2`

# Do not email if running in debug or in preparation mode
if [ ${DEBUG} != "yes" -a ${FLAG_P_IS_SET} != "yes" -a ${FLAG_C_IS_SET} != "yes" ]; then

MAIL_SUBJECT="${MAIL_SUBJECT}: ${DEPLOYMENT_STATUS}"
echo "`date`|${DEPLOYMENT_ID}|${L_CURRENT_USER}|${COMPONENT} ${VERSION} ${ENVIRONMENT}|${DEPLOYMENT_STATUS}" >> ${L_LOG_FILE2}
#mail_log

fi

if [ ${FLAG_C_IS_SET} = "yes" ]; then
echo "`date` CONFIGONLY|${DEPLOYMENT_ID}|${L_CURRENT_USER}|${COMPONENT} ${VERSION} ${ENVIRONMENT}|${DEPLOYMENT_STATUS}" >> ${L_LOG_FILE2}

fi

echo "LOG_URL ${LOG_URL}"

case ${DEPLOYMENT_STATUS} in
"SUCCESS")
		exit 0
		;;
"FAILED")	exit 1
		;;
"LOCKED")	exit 2
		;;
*)		exit 3
		;;
esac






