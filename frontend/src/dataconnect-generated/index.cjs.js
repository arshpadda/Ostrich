const { queryRef, executeQuery, validateArgsWithOptions, mutationRef, executeMutation, validateArgs, makeMemoryCacheProvider } = require('firebase/data-connect');

const connectorConfig = {
  connector: 'example',
  service: 'ostrich',
  location: 'us-central1'
};
exports.connectorConfig = connectorConfig;
const dataConnectSettings = {
  cacheSettings: {
    cacheProvider: makeMemoryCacheProvider()
  }
};
exports.dataConnectSettings = dataConnectSettings;

const createUserAccountRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'CreateUserAccount', inputVars);
}
createUserAccountRef.operationName = 'CreateUserAccount';
exports.createUserAccountRef = createUserAccountRef;

exports.createUserAccount = function createUserAccount(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(createUserAccountRef(dcInstance, inputVars));
}
;

const createNewSandboxRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'CreateNewSandbox', inputVars);
}
createNewSandboxRef.operationName = 'CreateNewSandbox';
exports.createNewSandboxRef = createNewSandboxRef;

exports.createNewSandbox = function createNewSandbox(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(createNewSandboxRef(dcInstance, inputVars));
}
;

const addAssetToSandboxRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'AddAssetToSandbox', inputVars);
}
addAssetToSandboxRef.operationName = 'AddAssetToSandbox';
exports.addAssetToSandboxRef = addAssetToSandboxRef;

exports.addAssetToSandbox = function addAssetToSandbox(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(addAssetToSandboxRef(dcInstance, inputVars));
}
;

const getUserSandboxesRef = (dc) => {
  const { dc: dcInstance} = validateArgs(connectorConfig, dc, undefined);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'GetUserSandboxes');
}
getUserSandboxesRef.operationName = 'GetUserSandboxes';
exports.getUserSandboxesRef = getUserSandboxesRef;

exports.getUserSandboxes = function getUserSandboxes(dcOrOptions, options) {
  
  const { dc: dcInstance, vars: inputVars, options: inputOpts } = validateArgsWithOptions(connectorConfig, dcOrOptions, options, undefined,false, false);
  return executeQuery(getUserSandboxesRef(dcInstance, inputVars), inputOpts && { fetchPolicy: inputOpts.fetchPolicy });
}
;
