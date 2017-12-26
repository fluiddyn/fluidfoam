FROM cbonamy/openfoam5-paraview54-swak4foam-without-nvidia
LABEL maintainer "cyrille.bonamy@legi.cnrs.fr"
# Ensure a sane environment
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DEBIAN_FRONTEND=noninteractive


# Update the image & install some tools
RUN apt-get update --fix-missing && \
    apt-get -y dist-upgrade && \
    apt-get install -y --no-install-recommends \
        python3 python-dev python-pip python-numpy python-scipy \
        python-matplotlib python-psutil && \
    rm -rf /var/lib/apt/lists/ && rm -rf /usr/share/doc/ && \
    rm -rf /usr/share/man/ && rm -rf /usr/share/locale/ && \
    apt-get clean

WORKDIR /home/openfoam
RUN /bin/bash -c "hg clone https://bitbucket.org/sedfoam/fluidfoam"
RUN /bin/bash -c "make"

#USER openfoam:openfoam
# Set the default entry point & arguments
ENTRYPOINT ["/bin/bash"]
# CMD        [""]

