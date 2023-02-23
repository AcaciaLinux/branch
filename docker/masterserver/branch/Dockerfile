FROM alpine
COPY branchmaster/ /branch/
COPY branchlog /branchlog/
COPY branchcommons /branchcommons/
COPY branchweb /branchweb/
RUN apk update && apk add python3 py3-pip make
RUN pip install setuptools && pip install bcrypt
RUN cd /branchlog/ && python3 setup.py sdist && pip install dist/branchlog-1.0.tar.gz
RUN cd /branchcommons/ && python3 setup.py sdist && pip install dist/branchcommons-1.0.tar.gz
RUN cd /branchweb/ && python3 setup.py sdist && pip install dist/branchweb-1.0.tar.gz
RUN cd /branch/ && make
COPY entry.sh /entry.sh
RUN chmod +x entry.sh
CMD /entry.sh
EXPOSE 27015/tcp
