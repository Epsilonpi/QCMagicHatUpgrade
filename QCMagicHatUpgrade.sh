#!/bin/bash
echo " Copy directory EPiQ_2f_3.0.0 in /home/pi/PycharmProjects/"
cp -r /home/pi/QCMagicHatUpgrade/upfiles/EPiQ_2f_3.0.0 /home/pi/PycharmProjects/
echo " Copy bashEPiQ in /home/pi/PycharmProjects/"
cp /home/pi/QCMagicHatUpgrade/upfiles/bashEPiQ /home/pi/PycharmProjects
echo " Copy qcmagichat in /home/pi/cprogs/qcmagichat"
cp /home/pi/QCMagicHatUpgrade/upfiles/qcmagichat /home/pi/cprogs/qcmagichat
echo " Copy QCMagicHat_3.0.0.X.production.hex in /home/pi/newfirmware"
cp /home/pi/QCMagicHatUpgrade/upfiles/QCMagicHat_3.0.0.X.production.hex /home/pi/newfirmware

