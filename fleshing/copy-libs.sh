#!/bin/bash
# This scripts copies all needed .so files into a MESA_VERSION specific lib directory
echo "Copying from $MESA_WORK_DIR/$MESA_VERSION-install and $MESA_WORK_DIR/drm-install into $MESA_VERSION-all-libs"
mkdir -p $MESA_WORK_DIR/$MESA_VERSION-all-libs
for f in `find $MESA_WORK_DIR/$MESA_VERSION-install $MESA_WORK_DIR/drm-install -name "*.so"`
do
  cp $f $MESA_WORK_DIR/$MESA_VERSION-all-libs
done
