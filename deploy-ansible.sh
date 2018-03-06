#!/bin/bash
source $JENKINS_HOME/jobs/$PROMOTED_JOB_NAME/builds/$PROMOTED_NUMBER/archive/maven_info.txt
TAGS="all"
# Run configuration steps when:
# UPDATE_CONFIGURATION contains true
if [[ "$UPDATE_CONFIGURATION" == 'true' ]]; then
        TAGS="$TAGS,configure"
fi
/bin/ansible-wrapper.sh $1 $2 $POM_GROUPID $POM_ARTIFACTID $POM_VERSION $TAGS

