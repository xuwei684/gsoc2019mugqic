#!/bin/bash
# Exit immediately on error
set -eu -o pipefail

SOFTWARE=fgbio
VERSION=0.6.1
ARCHIVE=${SOFTWARE}-${VERSION}.tar.gz
ARCHIVE_URL=https://github.com/fulcrumgenomics/${SOFTWARE}/archive/${VERSION}.tar.gz
SOFTWARE_DIR=${SOFTWARE,,}-${VERSION}

build() {
  cd $INSTALL_DOWNLOAD
  git clone --recursive https://github.com/fulcrumgenomics/fgbio.git -b $VERSION

  cd ${SOFTWARE}
  sbt assembly

  # Install software
  cd $INSTALL_DOWNLOAD
  mv -i ${SOFTWARE} $INSTALL_DIR/${SOFTWARE_DIR}
}

module_file() {
echo "\
#%Module1.0
proc ModulesHelp { } {
  puts stderr \"\tMUGQIC - $SOFTWARE \"
}
module-whatis \"$SOFTWARE\"

set             root                $INSTALL_DIR/$SOFTWARE_DIR
prepend-path    PATH                \$root/
"
}

# Call generic module install script once all variables and functions have been set
MODULE_INSTALL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source $MODULE_INSTALL_SCRIPT_DIR/install_module.sh $@
