
### Run with root

```js
sudo node index
```


### Run without root

```js
sudo setcap "cap_dac_override+ep cap_sys_rawio+ep" $(eval readlink -f `which node`)
```

```js
node index
```

https://gist.github.com/donaldh/8ef47058c0d5a68be413
