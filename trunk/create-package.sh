#!/bin/bash

# automatically create the debian package

build_dir=./packaging/archive/itunes-remote-applet_1.0-beta-1

rm -rf packaging/
mkdir -p $build_dir
cp src/*.py $build_dir
cp -R resources/* $build_dir

cd ./packaging/archive/

tar cfz ../itunes-remote-applet-1.0-beta-1.orig.tar.gz ./itunes-remote-applet_1.0-beta-1/ --exclude=.svn
# tar -xf itunes-remote-applet-1.0-beta-1.orig.tar.gz
# cd itunes-remote-applet
# dh_make -c apache -s -b -p itunes-remote-applet_1.0-beta-1
# cd debian
# rm *.ex *.EX
