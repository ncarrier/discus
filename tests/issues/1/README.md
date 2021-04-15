* **URL**: https://github.com/ncarrier/discus/issues/1
* **How to launch the reproducer**:

From the root of the discus source tree, run:

```
docker build . --tag discus-issue-1-reproducer --file tests/issues/1/Dockerfile
docker run --rm -it  -v ${PWD}:/workspace discus-issue-1-reproducer
```
* **failing revision**: 35d57a8a5d1e8cbae3a5358b7b98978ebe97c87f
