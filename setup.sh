# Clear anything already in lib/ except the README
shopt -s extglob
rm -rf lib/!(README.md)

# Install python dependencies
pip install -r requirements.txt -t lib/

