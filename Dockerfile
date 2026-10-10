FROM opencfd/openfoam-default:2512
LABEL maintainer "cyrille.bonamy@univ-grenoble-alpes.fr"
# Ensure a sane environment
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DEBIAN_FRONTEND=noninteractive


# Update the image & install some tools
RUN apt-get update --fix-missing && \
    apt-get -y dist-upgrade && \
    apt-get install -y --no-install-recommends \
        python3 python3-dev python3-pip python3-numpy \
        python3-matplotlib python3-psutil python3-scipy \
        python3-setuptools vera++ git doxygen && \
    rm -rf /var/lib/apt/lists/ && rm -rf /usr/share/doc/ && \
    rm -rf /usr/share/man/ && rm -rf /usr/share/locale/ && \
    apt-get clean

USER sudofoam:sudofoam
WORKDIR /home/sudofoam
RUN wget -qO- https://astral.sh/uv/install.sh | sh
RUN /bin/bash -c "git clone https://github.com/fluiddyn/fluidfoam"
WORKDIR /home/sudofoam/fluidfoam
RUN /bin/bash -c "export PATH=$PATH:/home/sudofoam/bin; make"
RUN /bin/bash -c "source /home/sudofoam/fluidfoam/.venv/bin/activate"

# Set the default entry point & arguments
ENTRYPOINT ["/bin/bash"]

