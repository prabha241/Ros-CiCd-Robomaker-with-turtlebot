#!/bin/bash
set -e
source "/home/$USERNAME/aws-robomaker-sample-application-cloudwatch/$APP_NAME/setup.bash"
if [[ -f "/usr/share/$GAZEBO_VERSION/setup.sh" ]]
then
    source /usr/share/$GAZEBO_VERSION/setup.sh
fi
printenv
exec "${@:1}"