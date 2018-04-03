FROM jboss/wildfly
MAINTAINER Steve Russell
EXPOSE 8080
EXPOSE 9990
ADD $WORKSPACE/$JOB_NAME/target/$JOB_NAME-$POM_VERSION.jar
RUN /opt/jboss/wildfly/bin/add-user.sh admin admin123 --silent
CMD ["/opt/jboss/wildfly/bin/standalone.sh", "-b", "0.0.0.0", "-bmanagement", "0.0.0.0"]
