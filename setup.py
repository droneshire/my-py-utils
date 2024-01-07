from setuptools import setup, find_packages

setup(
    name='my_package',
    version='1.0.0',
    description='A description of my package',
    author='Your Name',
    author_email='your@email.com',
    packages=find_packages(),
    install_requires=[
        # List any dependencies your package requires
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
