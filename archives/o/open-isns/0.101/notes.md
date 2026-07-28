# open-isns 0.101

- Builds the static `libisns` development library without optional OpenSSL
  authentication or OpenSLP discovery.
- The upstream suite contains 11 root-only daemon/network test programs. They
  are inventoried but are not executed in the unprivileged package consumer.
- The added consumer validates public status, portal parsing, and attribute-list
  APIs without starting a service or accessing privileged paths.
- Official OHOS test and CI results remain pending.
