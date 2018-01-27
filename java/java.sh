if ! echo ${PATH} | grep -q /app/jdk-9.0.4/bin ; then
   export PATH=/app/jdk-9.0.4/bin:${PATH}
fi
if ! echo ${PATH} | grep -q /app/jdk-9.0.4/jre/bin ; then
   export PATH=/app/jdk-9.0.4/jre/bin:${PATH}
fi
export JAVA_HOME=/app/jdk-9.0.4
export JRE_HOME=/app/jdk-9.0.4/jre
export CLASSPATH=.:/app/jdk-9.0.4/lib/tools.jar:/app/jdk-9.0.4/jre/lib/rt.jar
