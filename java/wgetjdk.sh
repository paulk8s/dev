#####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####

### Shell script to download Oracle JDK / JRE / Java binaries from Oracle website using terminal / command / shell prompt using wget.
### You can download all the binaries one-shot by just giving the BASE_URL.
### Script might be useful if you need Oracle JDK on Amazon EC2 env.
### Script is updated for every JDK release.

### Features:-
# 1. Resumes a broken / interrupted [previous] download, if any.
# 2. Renames the file to a proper name with including platform info.
# 3. Downloads the following from Oracle Website with one shell invocation.
#    a. Windows 64 and 32 bit;
#    b. Linux 64 and 32 bit;
#    c. API Docs;
#    d. You can add more to the list of downloads are per your requirement.

#####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####


## Latest JDK9 version is JDK9.0.1 released on 16th Jan, 2018.
BASE_URL_9=http://download.oracle.com/otn-pub/java/jdk/9.0.4+11/c2514751926b4512b076cc82f959763f/jdk-9.0.4_

#declare -a PLATFORMS=("linux-x64_bin.tar.gz" "windows-x64_bin.exe" "doc-all.zip")
declare -a PLATFORMS=("linux-x64_bin.tar.gz")
# declare -a PLATFORMS=("linux-x64_bin.rpm" "linux-x64_bin.tar.gz" "osx-x64_bin.dmg" "windows-x64_bin.exe" "solaris-sparcv9_bin.tar.gz" "doc-all.zip")

for platform in "${PLATFORMS[@]}"
do
    # wget -c --no-check-certificate --no-cookies --header "Cookie: oraclelicense=accept-securebackup-cookie" "${BASE_URL_9}${platform}"
    curl -C - -LR#OH "Cookie: oraclelicense=accept-securebackup-cookie" -k "${BASE_URL_9}${platform}"
done

#####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####   #####

##### Earlier JDK9 versions:
## 9u1 => http://download.oracle.com/otn-pub/java/jdk/9.0.1+11/jdk-9.0.1_
## 9u0 => http://download.oracle.com/otn-pub/java/jdk/9+181/jdk-9_