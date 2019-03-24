from setuptools import setup

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='ssh_honeypot',
      version='0.1.0',
      description="Special task SSH honeypot",
      packages=['ssh_honeypot'],
      python_requires='>=3.5.3',
      setup_requires=[
          'wheel',
      ],
      install_requires=[
          'asyncssh>=1.16.0',
          'aiosqlite>=0.9.0',
          'bashlex>=0.14',
      ],
      entry_points={
          'console_scripts': [
              'ssh-honeypot=ssh_honeypot.__main__:main',
          ],
      },
      classifiers=[
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Operating System :: OS Independent",
          "Development Status :: 4 - Beta",
          "Environment :: Console",
          "Environment :: No Input/Output (Daemon)",
          "Intended Audience :: System Administrators",
          "Natural Language :: English",
          "Topic :: Internet",
          "Topic :: Utilities",
          "Topic :: Security",
      ],
      long_description=long_description,
      long_description_content_type='text/markdown',
      zip_safe=True)
