#!/bin/bash
set -x

projectTypes=(`ls -1 $ANSIBLE_REPO/*.yml | grep -v variables_global.yml | sed -e 's,^.*/\([^\/]*\).yml$,\1,'`)
allEnvironments=(`ls -1 $ANSIBLE_REPO/roles/*/environments/* | sed -e 's,^.*\/,,' | sort | uniq`)

#array_contains () {
#    local seeking=$1; shift
#    local in=1
#    for element; do
#        if [[ $element == $seeking ]]; then
#            in=0
#            break
#        fi
#    done
#    return $in
#}


join() {
    local IFS=$1
    shift
    echo "$*"
}

function usage() {
    echo "Usage: $0 <environment> <project_type> <group_id> <artifact_id> <project_version> <steps>"
    echo "Parameters:"
    echo -n "* Environment = can be one of: "
    join ", " "${allEnvironments[@]}" 
    echo -n "* Project Type = can be one of: "
    join ", " "${projectTypes[@]}"
    echo
    echo "Required environment variables:"
    echo "ANSIBLE_REPO - location of repository with Ansible scripts"
    echo "ANSIBLE_LIBRARY - location of Ansible Modules Extras"
}

if [[ "$#" -ne 6 || -z "$ANSIBLE_REPO" || -z "$ANSIBLE_LIBRARY" ]]; then
    usage
    exit 1
fi

sshkey="$HOME/.ssh/id_rsa"
if [[ -r "${sshkey}_${1}" ]]; then
    sshkey="${sshkey}_${1}"
fi

export ANSIBLE_LOGIN_OPTS="--user=jenkins --private-key=$sshkey"

~/ansible/run.sh $1 $2 $3 $4 $5 $6
