FROM --platform=amd64 ubuntu:22.04

WORKDIR /usr/app

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    wget \
    curl \
    default-jre \
    libcairo2-dev

# copy requirements.txt to the working directory
COPY requirements.txt requirements.txt

# install python dependencies
RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir gdown

# install libreoffice
#RUN wget https://download.documentfoundation.org/libreoffice/stable/7.5.8/deb/x86_64/LibreOffice_7.5.8_Linux_x86-64_deb.tar.gz
#RUN wget https://downloadarchive.documentfoundation.org/libreoffice/old/7.4.6.2/deb/x86_64/LibreOffice_7.4.6.2_Linux_x86-64_deb.tar.gz
COPY LibreOffice_7.4.6.2_Linux_x86-64_deb.tar.gz LibreOffice_7.4.6.2_Linux_x86-64_deb.tar.gz
RUN tar -xzvf LibreOffice_7.4.6.2_Linux_x86-64_deb.tar.gz && cd LibreOffice_7.4.6.2_Linux_x86-64_deb/DEBS && dpkg -i *.deb
RUN rm -rf LibreOffice_7.4.6.2_Linux_x86-64_deb.tar.gz LibreOffice_7.4.6.2_Linux_x86-64_deb

# add to path
ENV PATH="${PATH}:/opt/libreoffice7.4/program/"

RUN wget https://bootstrap.pypa.io/get-pip.py
RUN /opt/libreoffice7.4/program/python get-pip.py
RUN /opt/libreoffice7.4/program/python -m pip install --no-cache-dir unoserver==1.6

# fix shebangs
RUN sed -i '1s/python\.bin/python/' "/opt/libreoffice7.4/program/python-core-3.8.16/bin/unoserver"
RUN sed -i '1s/python\.bin/python/' "/opt/libreoffice7.4/program/python-core-3.8.16/bin/unoconvert"
ENV PATH="/opt/libreoffice7.4/program/python-core-3.8.16/bin:${PATH}"

COPY resources resources
RUN curl https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -o resources/fasttext-models/lid.176.ftz

RUN apt-get install -y poppler-utils

COPY . .

ENTRYPOINT ["/bin/bash", "/usr/app/scripts/run_single_node.sh"]