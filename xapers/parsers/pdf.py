import subprocess

def parse(data):
    cmd = ['pdftotext', '-', '-']
    proc = subprocess.Popen(cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=open('/dev/null','w'),
                            )
    (stdout, stderr) = proc.communicate(input=data)
    proc.wait()
    return stdout.decode()
