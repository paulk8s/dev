#!/bin/sh

whocalled=$(basename $0)
DEPLOYENV=$(echo "${1}" | tr "[:lower:]" "[:upper:]")

# Input validation
DEPLOYENV=`echo ${DEPLOYENV} | awk '{print $1}' | sed 's/ //g'`
COMPONENT=`echo ${COMPONENT} | awk '{print $1}' | sed 's/ //g'`
VERSION=`echo ${VERSION} | awk '{print $1}' | sed 's/ //g'`


if [ "${whocalled}" != "deploy_universal_p10prod.sh" ]; then
	if [[ "${DEPLOY_ENV}" =~ "PROD" ]]; then
		echo "Invalid environment specified: ${DEPLOYENV}"
		exit 1
	fi
fi

if [ ! -e ../Components/${COMPONENT} ]; then 
  echo "${COMPONENT} not found in Components"
  echo "The following components are listed:"
  echo "========================="
  ls -1 ../Components/
  echo "========================="
  exit 1
fi

echo ""
echo "ENV: ${DEPLOYENV} -- COMP: ${COMPONENT} -- V: ${VERSION}"
echo ""
echo "If the above is incorrect, please stop the build now.  Will proceed in 10 seconds"
sleep 10

FORCE_DEPLOYMENT=`echo $FORCE_DEPLOYMENT | tr "[:lower:]" "[:upper:]"`
if [ "$FORCE_DEPLOYMENT" != "YES" ]; then
  ../deploy.ksh ${COMPONENT} ${VERSION} ${DEPLOYENV}
else
  ../deploy.ksh -f ${COMPONENT} ${VERSION} ${DEPLOYENV}
fi
