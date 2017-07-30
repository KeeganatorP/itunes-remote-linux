#!/bin/bash

function link_if_required {
	source_file=$1	
	link=$2
	if [ -h $link ]; then
		target=`readlink $link`
		if [ "$target" = "$source_file" ]; then
			echo "Link already set correctly: $link --> $target"
			return
		else
			echo "Removing incorrect link: $link --> $target"
			rm $link
		fi
	fi
	if [ ! -e $link ]; then
		echo "Create link: $link --> $source_file" 
		ln -s $source_file $link
	else
		echo "Non-link already exists in this location: $link"
		ls -l $link
	fi 

}

function force_link {
	source_file=$1	
	link=$2	
	echo "Force create link: $link --> $source_file" 
	rm -f $link
	ln -s $source_file $link
}

if [ ! -e /usr/lib/python2.6/dist-packages ]; then
	echo "Cannot find python 2.6 dist-packages dir: /usr/lib/python2.6/dist-packages"
	exit 200
fi

if [ `id -u` -ne "0" ]; then
	echo this script must be run as root
	exit 100
fi

install_dir=`dirname $0`
install_dir=`cd $install_dir; pwd`
echo "install dir: $install_dir"

force_link $install_dir/src/itunes-remote-applet.py /usr/bin/itunes-remote-applet.py

mkdir /usr/share/itunes-remote-applet

link_if_required $install_dir/resources/icons/apps/32x32/mimetypes/audio-x-generic.png /usr/share/itunes-remote-applet/audio-x-generic.png
link_if_required $install_dir/resources/icons/apps/32x32/emblems/emblem-default.png /usr/share/itunes-remote-applet/emblem-default.png
link_if_required $install_dir/resources/icons/apps/32x32/emblems/emblem-generic.png /usr/share/itunes-remote-applet/emblem-generic.png
force_link $install_dir/resources/pairing-gui.glade /usr/share/itunes-remote-applet/pairing-gui.glade

force_link $install_dir/resources/itunes-remote-applet.desktop /usr/share/applications/itunes-remote-applet.desktop

force_link $install_dir/resources/src/pairing_service.py /usr/lib/python2.6/dist-packages/pairing_service.py
force_link $install_dir/resources/src/dacp_serialisation.py /usr/lib/python2.6/dist-packages/dacp_serialisation.py
