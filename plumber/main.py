import os
import tempfile
import jinja2
import shutil
import yaml
import requests
from argparse import ArgumentParser



SUPPORTED_PROJECT_TYPES = ['python']
REGISTRY_URL = os.getenv('REGISTRY_URL')
MESOS_MASTER_HOST=os.getenv('MESOS_MASTER_HOST')
MESOS_PASS=os.getenv('MESOS_PASS')
templateLoader = jinja2.FileSystemLoader( searchpath="templates/" )
templateEnv = jinja2.Environment( loader=templateLoader )


def parse_manifest(filename):
    with open(filename, 'rb') as fh:
        c = yaml.load(fh)
    return c

def clean_checkout(path):
    """
    Clean up the current checkout
    """
    shutil.rmtree(path)

def marathon_deploy(c):
    """
    Deploy to marathon
    """
    name = 'tool-' + c['name']
    image = "{}/{}:latest".format(REGISTRY_URL, name)
    payload  = {
        "id": name,
        "container": {
            "docker": {
                "network": "BRIDGE",
                "image": image,
                "portMappings":
                [
                    {
                        "containerPort": 8080,
                        "hostPort": 0,
                        "protocol": "tcp"
                    }
                ]
            }
        },
        "cpus": 1.5,
        "mem": 1024
    }
    mesos_url = "http://{}:8080/v2/apps".format(MESOS_MASTER_HOST)
    r = requests.post(mesos_url, payload = json.dumps(payload), auth=('admin', MESOS_PASS))

def clone_repo(path):
    tmpdir = tempfile.mkdtemp(prefix='git_clone_' + os.basename(path))
    try:
        res = subprocess.check_output(['git', 'clone', path, tmpdir])
        return tmpdir
    except CalledProcessError, e:
        clean_checkout(tmpdir)
        raise

def get_dockerfile(c, path):
    """
    Creates the docker file from a template that's language-specific.
    """
    dockerfile = os.path.join(path, 'Dockerfile')
    template = templateEnv.get_template("Dockerfile.{}.tpl", c['type'])
    dockerdata = template.render(c)
    with open(dockerfile, 'w') as fh:
        fh.write(dockerdata)

def docker_build_and_push(c,dir):
    os.chdir(dir)
    # Todo: validate this, and everything else
    name = 'tool-' + c['name']
    tag = name + ':latest'
    # Build the docker container from the Dockerfile
    res = subprocess.check_output(['docker', 'build', '-t', name, '.'])
    res = subrpocess.check_output(['docker', 'tag', tag, REGISTRY_URL + '/' + tag])
    res = subprocess.check_output(['docker', 'push', REGISTRY_URL + '/' + tag])

def main():
    parser = ArgumentParser(description="Processing pipeline for building and deploying containers")
    parser.add_argument('repository_path', defalut=os.getcwd())
    args = parser.parse_args()
    clone_dir = clone_repo(args.repository_path)
    config_file = os.path.join(clone_dir, 'manifest.yaml')
    c = parse_manifest(config_file)
    project_name = c['name']
    project_type = c['type']
    # Dockerfile template rendering here
    get_dockerfile(c, clone_dir)
    docker_build_and_push(clone_dir)
    # TODO: we will have a central db with the max number of instances of a project we're gonna run.
    marathon_deploy(c)
    clean_checkout()
