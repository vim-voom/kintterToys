# This is an example bash script for installing kintterToys to /opt for all
# users on a typical Linux desktop distribution.
#
# This script must be run in the directory which contains program folder
# kintterToys. That is, if you extracted kintterToys in ~/Downloads, copy this
# script to ~/Downloads, then open terminal and do
#       $ cd ~/Downloads
#       $ sudo sh ./install_kintterToys.sh

# To uninstall, delete kintter* files:
#	$ sudo rm -rf /opt/kintterToys
#	$ sudo rm /usr/share/applications/kintterFind.desktop
#	$ sudo rm /usr/bin/kintterFind.sh


# make sure this script is run in correct directory
if [ ! -f ./kintterToys/kintterToys/kintterFind.py ]; then
    echo '... Wrong directory. Installation aborted. ...'
    exit
fi

echo '... removing /opt/kintterToys/ ...'
rm -rf /opt/kintterToys

echo '... copying kintterToys/ to /opt/ ...'
cp -r ./kintterToys/ /opt/

echo '... generating .pyc files ...'
find /opt/kintterToys/kintterToys -type f -name '*.pyc' -delete
python3 -m compileall /opt/kintterToys/kintterToys

echo '... normalizing permissions ...'
chmod 755 -R /opt/kintterToys
chmod -x+X -R /opt/kintterToys

echo '... copying .desktop file to /usr/share/applications/ ...'
cp ./kintterToys/examples/kintterFind.desktop /usr/share/applications/
chmod 644 /usr/share/applications/kintterFind.desktop

echo '... copying command line launcher to /usr/bin/ ...'
cp ./kintterToys/examples/kintterFind.sh /usr/bin/kintterFind.sh
chmod 755 /usr/bin/kintterFind.sh

echo '... finished ...'



