if ( "${path}" !~ */app/jdk-9.0.4/bin* ) then
   set path = ( /app/jdk-9.0.4/bin $path )
endif
if ( "${path}" !~ */app/jdk-9.0.4/jre/bin* ) then
    set path = ( /app/jdk-9.0.4/jre/bin $path )
endif
setenv JAVA_HOME /app/jdk-9.0.4
setenv JRE_HOME /app/jdk-9.0.4/jre
setenv CLASSPATH .:/app/jdk-9.0.4/lib/tools.jar:/app/jdk-9.0.4/jre/lib/rt.jar
