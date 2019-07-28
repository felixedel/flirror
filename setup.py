from setuptools import find_packages, setup

description = "A smartmirror based on Flask"

with open("README.md") as readme:
    long_description = readme.read()

requires = [
    "click",
    "flask",
    "google-api-python-client",
    "google-auth-httplib2",
    "google-auth-oauthlib",
    "pony",
    "pyowm",
    "python-dateutil",
]

setup(
    name="flirror",
    description=description,
    author="Benedikt Loeffler, Daniela Klahr, Felix Schmidt",
    # TODO email
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    install_requires=requires,
    url="https://github.com/felix-schmidt/flirror",
    # TODO license
    use_scm_version={"version_scheme": "post-release"},
    setup_requires=["setuptools_scm"],
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    entry_points={"console_scripts": ["flirror-crawler = flirror.crawler.main:main"]},
    # TODO classifiers for PyPI
)
