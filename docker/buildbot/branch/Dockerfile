FROM alpine as builder

# Build leaf
RUN apk update && apk add make curl-dev libcurl gcc g++ musl-dev libarchive-dev ncurses ncurses-dev git cmake libc-dev linux-headers

RUN 	git clone https://github.com/AcaciaLinux/leaf -b dev --depth=1 \
	&& cd leaf \
	&& git submodule update --recursive --init --depth=1 \
	&& mkdir build && cd build \
	&& cmake .. \
	&& make -j$(nproc) \
	&& make DESTDIR=/leafinstall install

FROM alpine

# Now build the real container
RUN	apk update \
	&& apk add python3 libcurl libarchive binutils python3-dev py3-pip curl-dev gcc linux-headers musl-dev \
	&& python3 -B -m pip install setuptools \
	&& python3 -B -m pip install pycurl \
	&& python3 -B -m pip install psutil \
	&& find / -name __pycache__ -exec rm -rf {} \; || true \
	&& apk del python3-dev curl-dev gcc linux-headers musl-dev

COPY branchbuildbot/ /branch/
COPY branchlog /branchlog/
COPY branchcommons /branchcommons/
COPY pyleaf /pyleaf/

RUN	apk add make \
	&& cd /branchlog/ && python3 setup.py sdist && python3 -B -m pip install dist/branchlog-*.tar.gz \
	&& cd /branchcommons/ && python3 setup.py sdist && python3 -B -m pip install dist/branchcommons-*.tar.gz \
	&& cd /pyleaf/ && python3 setup.py sdist && python3 -B -m pip install dist/pyleaf-*.tar.gz \
	&& cd /branch/ && make \
	&& apk del make \
	&& find / -name __pycache__ -exec rm -rf {} \; || true \
	&& rm -rf /branchlog \
	&& rm -rf /branchcommons \
	&& rm -rf /pyleaf \
	&& rm -rf /branch

# Create the branch config directory
RUN mkdir -pv /etc/branch
RUN mkdir -pv /branchworkdirectory

# Copy leaf
COPY --from=builder /leafinstall/* /

COPY entry.sh /entry.sh
COPY def_config.py /def_config.py

RUN chmod +x entry.sh

CMD /entry.sh
