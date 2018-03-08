#!/bin/bash
VERSION=$POM_VERSION
GROUPID=$POM_GROUPID
ARTIFACTID=$POM_ARTIFACTID
 
if [[ -f ${WORKSPACE}/artifact.info ]]; then
        IFS=':' read -r -a ga < ${WORKSPACE}/artifact.info
        GROUPID=${ga[0]}
        ARTIFACTID=${ga[1]}
fi
 
echo "export POM_VERSION=$VERSION" > ${WORKSPACE}/maven_info.txt
echo "export POM_GROUPID=$GROUPID" >> ${WORKSPACE}/maven_info.txt
echo "export POM_ARTIFACTID=$ARTIFACTID" >> ${WORKSPACE}/maven_info.txt