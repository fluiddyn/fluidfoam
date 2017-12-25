FROM python:3.6
LABEL maintainer "cyrille.bonamy@legi.cnrs.fr"
# Ensure a sane environment
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DEBIAN_FRONTEND=noninteractive


# Update the image & install some tools
RUN apt-get update --fix-missing && \
    apt-get -y dist-upgrade && \
    apt-get install -y --no-install-recommends \
    	wget mesa-utils libegl1-mesa libegl1-mesa-drivers libgl1-mesa-dri \
        libglapi-mesa libgd-tools imagemagick graphicsmagick mplayer mencoder \
        mjpegtools emacs gedit gedit-plugins gnuplot gnuplot-x11 \
        gnuplot-doc bash-completion bash-builtins libnss-wrapper vim nano tree \
        python3 python-dev python-pip python-numpy python-scipy python-matplotlib python-psutil \
        openmpi-bin libopenmpi-dev make flex gcc g++ libz-dev libfl-dev \
        curl bash-completion cmake libxt-dev \
        qt5-default qttools5-dev libqt5x11extras5-dev qtbase5-dev libqt5opengl5-dev libqt5sql5-sqlite \
        time freeglut3-dev meld ca-certificates && \
    rm -rf /var/lib/apt/lists/ && rm -rf /usr/share/doc/ && \
    rm -rf /usr/share/man/ && rm -rf /usr/share/locale/ && \
    apt-get clean

# Download the 5.0 OpenFoam sources, install, and clean
RUN mkdir -p /opt/openfoam/5.0 && wget -O /opt/openfoam/5.0/OFzip https://codeload.github.com/OpenFOAM/OpenFOAM-5.x/tar.gz/version-5.0 && \
    cd /opt/openfoam/5.0 && tar -xvf OFzip && rm OFzip && mv /opt/openfoam/5.0/OpenFOAM-5.x-version-5.0 /opt/openfoam/5.0/OpenFOAM-5.0 && \
    wget -O /opt/openfoam/5.0/TPzip https://codeload.github.com/OpenFOAM/ThirdParty-5.x/tar.gz/version-5.0 && tar -xvf TPzip && rm TPzip && \
    mv /opt/openfoam/5.0/ThirdParty-5.x-version-5.0 /opt/openfoam/5.0/ThirdParty-5.0 && \
    cd /opt/openfoam/5.0/OpenFOAM-5.0 && \
    /bin/bash -c "source etc/bashrc; ./Allwmake" && \
    cd /opt/openfoam/5.0/ThirdParty-5.0 && \
    /bin/bash -c "source /opt/openfoam/5.0/OpenFOAM-5.0/etc/bashrc; ./makeParaView -python -python-lib /usr/lib/x86_64-linux-gnu/libpython2.7.so.1.0 -cmake /usr/bin/cmake" && \
    /bin/bash -c "source /opt/openfoam/5.0/OpenFOAM-5.0/etc/bashrc && wmRefresh" && \
    rm -rf /opt/openfoam/5.0/ThirdParty-5.0/build && \
    /bin/bash -c "find /opt/openfoam -name \"*.o\" -exec rm -f {} \;" && \
    /bin/bash -c "find /opt/openfoam -name \".git*\" -exec rm -rf {} \;" && \
    /bin/bash -c "find /opt/openfoam -name \".svn*\" -exec rm -rf {} \;" && \
    sync

RUN echo "source /opt/openfoam/5.0/OpenFOAM-5.0/etc/bashrc" >> ${HOME}/.bashrc && \
    sync

RUN /bin/bash -c "source /opt/openfoam/5.0/OpenFOAM-5.0/etc/bashrc && pip install setuptools && \
    pip install wheel && pip install PyFoam mercurial"

WORKDIR /opt
RUN /bin/bash -c "hg clone http://hg.code.sf.net/p/openfoam-extend/swak4Foam -r compile_of5.0"
WORKDIR /opt/swak4Foam
RUN /bin/bash -c "source /opt/openfoam/5.0/OpenFOAM-5.0/etc/bashrc && ./maintainanceScripts/compileRequirements.sh"
RUN /bin/bash -c "source /opt/openfoam/5.0/OpenFOAM-5.0/etc/bashrc && ./Allwmake"
RUN /bin/bash -c "source /opt/openfoam/5.0/OpenFOAM-5.0/etc/bashrc && ./maintainanceScripts/copySwakFilesToSite.sh"

#create user openfoam and set environment directories
RUN useradd -ms /bin/bash openfoam
WORKDIR /home/openfoam
RUN /bin/bash -c "hg clone https://bitbucket.org/sedfoam/fluidfoam"
RUN /bin/bash -c "make"

#USER openfoam:openfoam
# Set the default entry point & arguments
ENTRYPOINT ["/bin/bash"]
# CMD        [""]

