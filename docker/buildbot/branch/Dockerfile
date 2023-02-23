FROM alpine
COPY branchbuildbot/ /branch/
COPY branchlog /branchlog/
COPY branchcommons /branchcommons/
COPY pyleaf /pyleaf/
RUN apk update && apk add python3-dev make python3 py3-pip make curl-dev libcurl gcc g++ clang musl-dev libarchive-dev ncurses ncurses-dev git cmake
RUN git clone https://github.com/AcaciaLinux/leaf -b dev --recursive && cd leaf && mkdir build && cd build && cmake .. && make -j12 && make install
RUN pip install setuptools && pip install pycurl && pip install psutil
RUN cd /branchlog/ && python3 setup.py sdist && pip install dist/branchlog-1.0.tar.gz
RUN cd /branchcommons/ && python3 setup.py sdist && pip install dist/branchcommons-1.0.tar.gz
RUN cd /pyleaf/ && python3 setup.py sdist && pip install dist/pyleaf-1.0.tar.gz
RUN cd /branch/ && make
COPY entry.sh /entry.sh
RUN chmod +x entry.sh
CMD /entry.sh
