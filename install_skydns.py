#!/usr/bin/python

import json
import os
from subprocess import Popen, PIPE

BASE_PATH = '/var/lib/kubelet/pods/'
EMPTY_DIR_PATH = 'volumes/kubernetes.io~empty-dir'
SECRET_DIR_PATH = 'volumes/kubernetes.io~secret'
SELINUX_LABEL = 'svirt_sandbox_file_t'

KUBELET_PATH = '/etc/kubernetes/kubelet'
KUBELET_ARGS = ['--cluster_dns=10.254.0.10', '--cluster_domain=cluster.local']
#KUBELET_ARGS = 'KUBELET_ARGS="--cluster_dns=10.254.0.10 --cluster_domain=cluster.local"'


def run_cmd(cmd, checkexitcode=True, stdin=None):
    """
    Runs a command with its arguments and returns the results. If
    the command gives a bad exit code then a CalledProcessError
    exceptions is raised, just like if check_call() were called.

    Args:
        checkexitcode: Raise exception on bad exit code
        stdin: input string to pass to stdin of the command

    Returns:
        ec:     The exit code from the command
        stdout: stdout from the command
        stderr: stderr from the command
    """
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(stdin)
    ec = p.returncode
    #print "\n<<< stdout >>>\n%s<<< end >>>\n" % stdout
    #print "\n<<< stderr >>>\n%s<<< end >>>\n" % stderr

    # If the exit code is an error then raise exception unless
    # we were asked not to.
    if checkexitcode:
        if ec != 0:
            raise Exception("cmd: %s failed: \n%s" % (str(cmd), stderr))

    return ec, stdout, stderr


def get_pod_uid():
    cmd = '/usr/bin/kubectl get pods'
    ec, stdout, stderr = run_cmd(cmd.split())

    for line in stdout.split('\n'):
        if 'kube-dns' in line:
            return line.split()[0]


def get_kube_dns_folder():
    cmd = '/usr/bin/kubectl  get pod {} -o json'.format(get_pod_uid())
    ec, stdout, stderr = run_cmd(cmd.split())
    stdout_dict = json.loads(stdout)
    return stdout_dict['metadata']['uid']

def start_sky_dns():
    cmd = '/home/vagrant/.virtualenvs/atomic/bin/atomicapp run projectatomic/skydns-atomicapp'
    ec, stdout, stderr = run_cmd(cmd.split())


def change_selinux_labels(path):
    cmd = '/usr/bin/chcon -R -t svirt_sandbox_file_t {}'.format(path)
    ec, stdout, stderr = run_cmd(cmd.split())

def change_kubelet_args():
    f = open(KUBELET_PATH)
    text = f.readlines()
    f.close()

    new_file = []
    for line in text:
        if 'KUBELET_ARGS' in line:
            args = line.split('"')[1:-1]
            args.extend(KUBELET_ARGS)
            line = 'KUBELET_ARGS="{}"\n'.format(' '.join(args))
        new_file.append(line)

    f = open(KUBELET_PATH, 'w')
    text = f.writelines(new_file)
    f.close()

def restart_kubelet_service():
    cmd = '/usr/bin/systemctl restart kubelet.service'
    run_cmd(cmd.split())

def main():
    start_sky_dns()
    print 'Deployed skydns'
    
    kube_dns_folder = get_kube_dns_folder()
    empty_dir_path = os.path.join(BASE_PATH, kube_dns_folder, EMPTY_DIR_PATH)
    secret_dir_path = os.path.join(BASE_PATH, kube_dns_folder, SECRET_DIR_PATH)
    print 'empty_dir: {}\nsecret_dir: {}'.format(empty_dir_path, secret_dir_path)

    for path in [empty_dir_path, secret_dir_path]:
        change_selinux_labels(path)
    print 'changed contexts successfully'

    change_kubelet_args()
    restart_kubelet_service()
    print 'Restarted the Kubelet service'

main()
