import subprocess
import os

SIGNAL_CLI_PATH = "/Users/svenfriess/Downloads/signal-cli-0.13.18/bin/signal-cli"
SIGNAL_NUMBER = "+4915755901211"
JAVA_HOME_PATH = "/opt/homebrew/opt/openjdk@21"

env = os.environ.copy()
env["JAVA_HOME"] = JAVA_HOME_PATH

print("👂 Starte manuelles signal-cli receive...")

process = subprocess.Popen(
    [SIGNAL_CLI_PATH, "-u", SIGNAL_NUMBER, "receive"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env
)

while True:
    output = process.stdout.readline()
    if output:
        print("📥 STDOUT:", output.strip())
    err = process.stderr.readline()
    if err:
        print("❗ STDERR:", err.strip())
