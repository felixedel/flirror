FROM backstopjs/backstopjs:4.4.2

WORKDIR /src

# Install python3.7 (flirror requires at least 3.6) and and appropriate pip
# version.
# Installing pip via apt is not the recommended way, but should be sufficient
# as we are not installing multiple python versions and/or environments inside
# this container.
RUN add-apt-repository "deb http://ftp.de.debian.org/debian testing main" \
  && apt-get -y update \
  && apt-get -y -t testing install \
    python3.6 \
    python3-pip \
  && apt-get -y install sqlite3 \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get -y clean

# Backstop JS expects everything in the /src directory
COPY . /src

# Install flirror (mainly used to get all dependencies installed)
RUN python3 -m pip install -e . \
  && python3 -m pip install -r test-requirements.txt

# Backstop JS sets the entrypoint to "backstop" which doesn't allow us to
# execute an arbitrary bash script. Thus, reset the entrypoint to /bin/sh.
ENTRYPOINT [ "helpers/run-backstop.py" ]
