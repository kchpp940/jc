import ast
import setuptools

def _get_release():
    with open('jc/lib.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if node.targets[0].id == '__release__':
                return ast.literal_eval(node.value)
    raise RuntimeError('Unable to find __release__ dict in jc/lib.py')

release = _get_release()

with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name=release['name'],
    version=release['version'],
    author=release['author'],
    author_email=release['author_email'],
    description=release['description'],
    install_requires=release['install_requires'],
    license=release['license'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires=release['python_requires'],
    url=release['website'],
    packages=setuptools.find_packages(exclude=['*.tests', '*.tests.*', 'tests.*', 'tests']),
    package_data={'jc': ['py.typed']},
    entry_points={
        'console_scripts': [
            'jc=jc.cli:main'
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Utilities'
    ]
)
