#!/bin/sh

if ! [ -f /etc/branch/buildbot.conf ]; then
	echo "[init] Creating default config..."
	python3 /def_config.py

	if ! [ -z "${BRANCH_SERVERURL}" ]; then
		echo "[init] Set the server address to $BRANCH_SERVERURL"
		sed -i "s/serveraddress.*/serveraddress = ${BRANCH_SERVERURL}/g" /etc/branch/buildbot.conf
	fi

	if ! [ -z "${BRANCH_SERVERPORT}" ]; then
		echo "[init] Set the server port to $BRANCH_SERVERPORT"
		sed -i "s/serverport.*/serverport = ${BRANCH_SERVERPORT}/g" /etc/branch/buildbot.conf
	fi

	if ! [ -z "${BRANCH_AUTHKEY}" ]; then
		echo "[init] Set the authkey to $BRANCH_AUTHKEY"
		sed -i "s/authkey.*/authkey = ${BRANCH_AUTHKEY}/g" /etc/branch/buildbot.conf
	fi

	if [ -z "${BRANCH_IDENTIFIER}" ]; then
		echo "[init] Generating identifier from hostname..."
		sed -i "s/identifier.*/identifier = docker-$(cat /etc/hostname)/g" /etc/branch/buildbot.conf
	else
		echo "[init] Set identifier to $BRANCH_IDENTIFIER"
		sed -i "s/identifier.*/identifier = ${BRANCH_IDENTIFIER}/g" /etc/branch/buildbot.conf
	fi

	echo "[init] Used config:"
	cat /etc/branch/buildbot.conf
fi

cd /branchworkdirectory/
branchbuildbot
