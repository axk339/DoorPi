#!/bin/bash
######################################
#
# Doorpi Installations Modul
#
# 13.9.21  v0.2.1 - Installation Doorpi
#
######################################


PACKAGE="DoorPi"
PROJECT="doorpi"

USER=$(whoami)
GROUP=$(id -g -n "$USER")

result=""
BackupPath="/mnt/user"
TransferPath="/mnt/conf/"
GitTarget="/usr/local/src/doorpicon"
TempDoorpi="/tmp/DoorPi"
TempConfig="/tmp/doorpicon"
DoorpiSetup="/usr/local/lib/python2.7/dist-packages/DoorPi*"
newpassword="doorpi"
doorpiconf="/usr/local/etc/DoorPi"

GET_PIP_URL="https://bootstrap.pypa.io/pip/3.6/get-pip.py"
GITCLONEHTTPS="https://github.com/emphasize/DoorPi"
BRANCH="bugfix/setuptools"

BASE_PATH=$(dirname "$(readlink -e "$0")")
DATADIR="$BASE_PATH"/data
declare -A DATA_DESTINATION
DATA_DESTINATION["doorpi.service.in"]="/usr/local/lib/systemd/system/doorpi.service"
DATA_DESTINATION["doorpi.socket"]="/usr/local/lib/systemd/system/doorpi.socket"
ScripName=${0##*/}

ADDITIONAL_SYSTEM_REQUIREMENTS=""

python2V=false
version=v0.2.1


Debug=0
#[ Debug == 1 ] || set -x

# Root Rechte überprüfen
if [ "$EUID" -ne 0 ]; then
    echo "Programm muss mit ROOT Rechten ausgeführt werden"
    exit 1
fi

StartDaemon (){

    sudo systemctl start doorpi.service
    result="Doorpi daemon gestartet"
}

StopDaemon (){

    sudo systemctl stop doorpi.service
    result="Doorpi daemon gestopt"
}

InstallSamba (){

    if [ ! -d $BackupPath ]; then
        mkdir -p $BackupPath
        chown :pi -R $BackupPath
        chmod g+rw -R $BackupPath
    fi

    ln -s /usr/local/etc/DoorPi/  /mnt/conf

    #Samba
    sudo DEBIAN_FRONTEND=noninteractive apt-get -yq install -y samba samba-common smbclient
    cp -r $BASE_PATH"/conf/smb.conf" /etc/samba/

    sudo service smbd restart
    sudo service nmbd restart

    (echo $newpassword; echo $newpassword) | smbpasswd -a pi -s

    result="Samba wurde installiert"
}

DoorpiBackup (){

    if [ ! -d $BackupPath ]; then
        result="Das Backup ist fehlgeschlagen, /mnt/backup Verzeichnis nicht vorhanden"
        return
    fi

    doorpiconf1="$doorpiconf/conf"
    doorpiconf2="$doorpiconf/log"
    doorpiconf3="$doorpiconf/media"
    today=`date +%Y-%m-%d_%H%M%S_`$HOSTNAME"_doorpiconf.tar.gz"

    tar cfvz $BackupPath/$today $doorpiconf1 $doorpiconf2 $doorpiconf3

    if [ $? == 0 ]; then
        result="Das Backup <  $today  > wurde erstellt"
        return

    else
        result="Das Backup ist fehlgeschlagen"
        return
    fi
}

DoorpiRestore (){

    if [ ! -d $BackupPath ]; then
        result="Das Restore ist fehlgeschlagen, /mnt/backup Verzeichnis nicht vorhanden"
        return
    fi

    fnames=""
    bakupadv="$BackupPath/*.tar.gz"
    # Verzeichnis auf dateien durchsuchen
    for file in $bakupadv; do
      fnames+=${file##*/},"",
    done
    echo $fnames
    # Dateien in Array schreiben
    IFS=',' read -r -a array <<< "$fnames"
    echo ${array[@]}
    restoreCHOICE=$(
    dialog --title "Wähle Doorpi Konfiguration zur Wiederherstellung" --menu "\n Bitte Wiederherstellungs Datei auswählen" 16 78 5 \
                      "${array[@]}" 3>&2 2>&1 1>&3
	)

    if [ $restoreCHOICE != "" ] ; then
        restorefile=$BackupPath/$restoreCHOICE

        StopDaemon
        tar -xvf $restorefile
        StartDaemon

        result="Wiederherstellung erfolgreich abgeschlossen !"

    else
        result="Wiederherstellung wurde abgebrochen !"

    fi
}

function found_exe() {
    hash "$1" 2>/dev/null
}

function os_is() {
    [[ $(grep "^ID=" /etc/os-release | awk -F'=' '/^ID/ {print $2}' | sed 's/\"//g') == $1 ]]
}

function os_is_like() {
    grep "^ID_LIKE=" /etc/os-release | awk -F'=' '/^ID_LIKE/ {print $2}' | sed 's/\"//g' | grep -q "\\b$1\\b"
}

function preinstall() {
    if found_exe zypper ; then
        # OpenSUSE
        $SUDO zypper install -y git python3 python3-devel dialog
    elif found_exe yum && os_is centos ; then
        # CentOS
        $SUDO yum install epel-release
        $SUDO yum install -y cmake git python3-devel python3-pip dialog curl
    elif found_exe yum && os_is rhel ; then
        # Redhat Enterprise Linux
        $SUDO yum install -y cmake git python3-devel dialog curl
    elif os_is_like debian || os_is debian || os_is_like ubuntu || os_is ubuntu || os_is linuxmint; then
        # Debian / Ubuntu / Mint
        $SUDO apt-get install git python3 python3-pip python3-dev python3-setuptools dialog curl
    elif os_is_like fedora || os_is fedora; then
        # Fedora
        $SUDO dnf install -y git python3 python3-devel python3-pip python3-setuptools python3-virtualenv dialog curl
    elif found_exe pacman && (os_is arch || os_is_like arch); then
        # Arch Linux
        $SUDO pacman -S --needed --noconfirm git python python-pip python-setuptools python-virtualenv dialog curl
    elif found_exe emerge && os_is gentoo; then
        # Gentoo Linux
        $SUDO emerge --noreplace dev-vcs/git dev-lang/python dev-python/setuptools dev-python/requests dev-util/dialog
    elif found_exe apk && os_is alpine; then
        # Alpine Linux
        $SUDO apk add --virtual git python3 py3-pip py3-setuptools py3-virtualenv dialog curl
    else
    	echo
        echo "Could not find package manager. Make sure to manually install: git python3 python-setuptools python-venv \n"
        exit 1
    fi

    curl "${GET_PIP_URL}" | "/bin/python3" -

    if git rev-parse --git-dir > /dev/null 2>&1; then
        if [[ $BRANCH != "master" ]] ; then
            git checkout "$BRANCH" 2&1> /dev/null
        fi
    else
        git clone "$GITCLONEHTTPS" 2&1> /dev/null
        cd "$PROJECT" 2&1> /dev/null
        if [[ $BRANCH != "master" ]] ; then
            git checkout "$BRANCH" 2&1> /dev/null
        fi
    fi
}

function prepare_install() {
    PREFIX=$1
    if [ -z $PREFIX ] ; then
        PREFIX="$HOME"/.local/share
    fi

    if [ $PREFIX == "/usr" ] || [ $PREFIX == "/usr/local" ] ; then
        WORKING_DIR="$PREFIX"/etc/"$PROJECT"
    else
        WORKING_DIR="$PREFIX"/"$PROJECT"
    fi

    CONFIG_DIR="$WORKING_DIR"/conf
    CONFIG_FILE="$CONFIG_DIR"/"$PROJECT".ini
    LOG_FILE=/var/log/"$PROJECT"/"$PROJECT".log
    LOG_DIR=/var/log/"$PROJECT"

    declare -A substkeys
    substkeys["!!package!!"]="$PACKAGE"
    substkeys["!!project!!"]="$PROJECT"
    substkeys["!!prefix!!"]="$PREFIX"
    substkeys["!!cfgfile!!"]="$CONFIG_FILE"
    substkeys["!!cfgdir!!"]="$CONFIG_DIR"
    substkeys["!!logfile!!"]="$LOG_FILE"
    substkeys["!!user!!"]="$USER"
    substkeys["!!group!!"]="$GROUP"

    for FILE in "$DATADIR"/* ; do
        destination="${DATA_DESTINATION[$( basename "$FILE")]}"
        for v in "${!substkeys[@]}"; do
            if [[ "$FILE" == *.in ]] ; then
                sed -i "s|$v|${substkeys[$v]}|g" "$FILE"
            fi
        done
        if [[ -n $destination ]] ; then
            [[ ! -d $destination ]] && sudo mkdir -p $(dirname "$destination")
            sudo cp "$FILE" "$destination"
        fi
    done

    for folder in "$CONFIG_DIR" "$LOG_DIR"; do
        [[ $folder != /home/* ]] && USE_SUDO=1
        if [ $USE_SUDO -eq 1 ]; then
            $sudo mkdir -p "$folder"
            USE_SUDO=""
        else
            mkdir -p "$folder"
        fi
    done

    if [ ! -f "$CONFIG_FILE" ]; then
        [[ "$CONFIG_FILE" != /home/* ]] && USE_SUDO=1
        if [ $USE_SUDO -eq 1 ]; then
            $sudo touch "$CONFIG_FILE"
            echo 'base_path = "'"$CONFIG_DIR"'"' | $sudo tee $CONFIG_FILE
            USE_SUDO=""
        else
            touch "$CONFIG_FILE"
            echo 'base_path = "'"$CONFIG_DIR"'"' > $CONFIG_FILE
        fi
    fi
}

if  [ ! -f .installed ] ; then
    preinstall
    touch .installed
fi

while [ 1 ]
do
    CHOICE=$(
        dialog --title "Willkomen im Doorpi Konfiguration Menu $version" --menu "\n " 16 78 7 \
        "10" "| Doorpi Installation    Neuinstallation Doorpi"  3>&2 2>&1 1>&3
    )

    result=$(whoami)
    case $CHOICE in

            "")
                clear
                exit
                ;;

            "10")
                clear
                PREFIX=$(
                    dialog --inputbox '''PREFIX / Where to install to?
                    (/usr/local is recommended atm)''' 9 50 '' 3>&2 2>&1 1>&3
                )
                prepare_install "$PREFIX"
                sudo python3 -m pip install . --prefix $PREFIX | dialog --progressbox 30 100
	            ;;

            "20")
                StartDaemon
                read -r result < result
	            ;;

            "25")
                StopDaemon
                read -r result < result
	            ;;

            "30")
                DoorpiBackup
                read -r result < result
                ;;

            "40")
                DoorpiRestore
                read -r result < result
                ;;

            "60")
                InstallSamba
                read -r result < result
                ;;

            "70")
                read -r result < result
                ;;
    esac
    dialog --msgbox "$result" 16 78
done
clear
exit
