# This is an example bash script for installing kintterToys to /opt on a
# typical Linux desktop distribution.
#
# Run this script from it's directory in a terminal like this:
#       $ sudo sh ./install_kintterToys.sh
#
# To uninstall, delete kintter* files:
#	$ sudo rm -rf /opt/kintterToys
#	$ sudo rm /usr/share/applications/kintterFind.desktop
#	$ sudo rm /usr/bin/kintterFind.sh

cd ..
# make sure this script is run from correct directory
if [ ! -f ./kintterToys/kintterFind.py ]; then
    echo '... Wrong directory. Installation aborted.'
    exit
fi

echo '... removing /opt/kintterToys/'
rm -rf /opt/kintterToys

echo '... copying files to /opt/kintterToys/'
mkdir /opt/kintterToys
cp -r * /opt/kintterToys

echo '... generating .pyc files'
find /opt/kintterToys/kintterToys -type f -name '*.pyc' -delete
python3 -m compileall /opt/kintterToys/kintterToys

echo '... normalizing permissions'
chmod 755 -R /opt/kintterToys
chmod -x+X -R /opt/kintterToys

echo '... copying .desktop file to /usr/share/applications/'
cp ./install/kintterFind.desktop /usr/share/applications/
chmod 644 /usr/share/applications/kintterFind.desktop

echo '... copying command line launcher to /usr/bin/'
cp ./install/kintterFind.sh /usr/bin/kintterFind.sh
chmod 755 /usr/bin/kintterFind.sh

echo '... finished'


