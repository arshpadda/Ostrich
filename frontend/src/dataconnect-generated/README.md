# Generated TypeScript README
This README will guide you through the process of using the generated JavaScript SDK package for the connector `example`. It will also provide examples on how to use your generated SDK to call your Data Connect queries and mutations.

***NOTE:** This README is generated alongside the generated SDK. If you make changes to this file, they will be overwritten when the SDK is regenerated.*

# Table of Contents
- [**Overview**](#generated-javascript-readme)
- [**Accessing the connector**](#accessing-the-connector)
  - [*Connecting to the local Emulator*](#connecting-to-the-local-emulator)
- [**Queries**](#queries)
  - [*GetUserSandboxes*](#getusersandboxes)
- [**Mutations**](#mutations)
  - [*CreateUserAccount*](#createuseraccount)
  - [*CreateNewSandbox*](#createnewsandbox)
  - [*AddAssetToSandbox*](#addassettosandbox)

# Accessing the connector
A connector is a collection of Queries and Mutations. One SDK is generated for each connector - this SDK is generated for the connector `example`. You can find more information about connectors in the [Data Connect documentation](https://firebase.google.com/docs/data-connect#how-does).

You can use this generated SDK by importing from the package `@dataconnect/generated` as shown below. Both CommonJS and ESM imports are supported.

You can also follow the instructions from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#set-client).

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig } from '@dataconnect/generated';

const dataConnect = getDataConnect(connectorConfig);
```

## Connecting to the local Emulator
By default, the connector will connect to the production service.

To connect to the emulator, you can use the following code.
You can also follow the emulator instructions from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#instrument-clients).

```typescript
import { connectDataConnectEmulator, getDataConnect } from 'firebase/data-connect';
import { connectorConfig } from '@dataconnect/generated';

const dataConnect = getDataConnect(connectorConfig);
connectDataConnectEmulator(dataConnect, 'localhost', 9399);
```

After it's initialized, you can call your Data Connect [queries](#queries) and [mutations](#mutations) from your generated SDK.

# Queries

There are two ways to execute a Data Connect Query using the generated Web SDK:
- Using a Query Reference function, which returns a `QueryRef`
  - The `QueryRef` can be used as an argument to `executeQuery()`, which will execute the Query and return a `QueryPromise`
- Using an action shortcut function, which returns a `QueryPromise`
  - Calling the action shortcut function will execute the Query and return a `QueryPromise`

The following is true for both the action shortcut function and the `QueryRef` function:
- The `QueryPromise` returned will resolve to the result of the Query once it has finished executing
- If the Query accepts arguments, both the action shortcut function and the `QueryRef` function accept a single argument: an object that contains all the required variables (and the optional variables) for the Query
- Both functions can be called with or without passing in a `DataConnect` instance as an argument. If no `DataConnect` argument is passed in, then the generated SDK will call `getDataConnect(connectorConfig)` behind the scenes for you.

Below are examples of how to use the `example` connector's generated functions to execute each query. You can also follow the examples from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#using-queries).

## GetUserSandboxes
You can execute the `GetUserSandboxes` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
getUserSandboxes(options?: ExecuteQueryOptions): QueryPromise<GetUserSandboxesData, undefined>;

interface GetUserSandboxesRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (): QueryRef<GetUserSandboxesData, undefined>;
}
export const getUserSandboxesRef: GetUserSandboxesRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
getUserSandboxes(dc: DataConnect, options?: ExecuteQueryOptions): QueryPromise<GetUserSandboxesData, undefined>;

interface GetUserSandboxesRef {
  ...
  (dc: DataConnect): QueryRef<GetUserSandboxesData, undefined>;
}
export const getUserSandboxesRef: GetUserSandboxesRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the getUserSandboxesRef:
```typescript
const name = getUserSandboxesRef.operationName;
console.log(name);
```

### Variables
The `GetUserSandboxes` query has no variables.
### Return Type
Recall that executing the `GetUserSandboxes` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `GetUserSandboxesData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface GetUserSandboxesData {
  sandboxes: ({
    id: UUIDString;
    title: string;
    createdAt: TimestampString;
    assets_on_sandbox: ({
      type: string;
      label?: string | null;
      positionX: number;
      positionY: number;
    })[];
  } & Sandbox_Key)[];
}
```
### Using `GetUserSandboxes`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, getUserSandboxes } from '@dataconnect/generated';


// Call the `getUserSandboxes()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await getUserSandboxes();

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await getUserSandboxes(dataConnect);

console.log(data.sandboxes);

// Or, you can use the `Promise` API.
getUserSandboxes().then((response) => {
  const data = response.data;
  console.log(data.sandboxes);
});
```

### Using `GetUserSandboxes`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, getUserSandboxesRef } from '@dataconnect/generated';


// Call the `getUserSandboxesRef()` function to get a reference to the query.
const ref = getUserSandboxesRef();

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = getUserSandboxesRef(dataConnect);

// Call `executeQuery()` on the reference to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeQuery(ref);

console.log(data.sandboxes);

// Or, you can use the `Promise` API.
executeQuery(ref).then((response) => {
  const data = response.data;
  console.log(data.sandboxes);
});
```

# Mutations

There are two ways to execute a Data Connect Mutation using the generated Web SDK:
- Using a Mutation Reference function, which returns a `MutationRef`
  - The `MutationRef` can be used as an argument to `executeMutation()`, which will execute the Mutation and return a `MutationPromise`
- Using an action shortcut function, which returns a `MutationPromise`
  - Calling the action shortcut function will execute the Mutation and return a `MutationPromise`

The following is true for both the action shortcut function and the `MutationRef` function:
- The `MutationPromise` returned will resolve to the result of the Mutation once it has finished executing
- If the Mutation accepts arguments, both the action shortcut function and the `MutationRef` function accept a single argument: an object that contains all the required variables (and the optional variables) for the Mutation
- Both functions can be called with or without passing in a `DataConnect` instance as an argument. If no `DataConnect` argument is passed in, then the generated SDK will call `getDataConnect(connectorConfig)` behind the scenes for you.

Below are examples of how to use the `example` connector's generated functions to execute each mutation. You can also follow the examples from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#using-mutations).

## CreateUserAccount
You can execute the `CreateUserAccount` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
createUserAccount(vars: CreateUserAccountVariables): MutationPromise<CreateUserAccountData, CreateUserAccountVariables>;

interface CreateUserAccountRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateUserAccountVariables): MutationRef<CreateUserAccountData, CreateUserAccountVariables>;
}
export const createUserAccountRef: CreateUserAccountRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
createUserAccount(dc: DataConnect, vars: CreateUserAccountVariables): MutationPromise<CreateUserAccountData, CreateUserAccountVariables>;

interface CreateUserAccountRef {
  ...
  (dc: DataConnect, vars: CreateUserAccountVariables): MutationRef<CreateUserAccountData, CreateUserAccountVariables>;
}
export const createUserAccountRef: CreateUserAccountRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the createUserAccountRef:
```typescript
const name = createUserAccountRef.operationName;
console.log(name);
```

### Variables
The `CreateUserAccount` mutation requires an argument of type `CreateUserAccountVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface CreateUserAccountVariables {
  username: string;
  email: string;
  avatarUrl?: string | null;
  bio?: string | null;
}
```
### Return Type
Recall that executing the `CreateUserAccount` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `CreateUserAccountData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface CreateUserAccountData {
  user_insert: User_Key;
}
```
### Using `CreateUserAccount`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, createUserAccount, CreateUserAccountVariables } from '@dataconnect/generated';

// The `CreateUserAccount` mutation requires an argument of type `CreateUserAccountVariables`:
const createUserAccountVars: CreateUserAccountVariables = {
  username: ..., 
  email: ..., 
  avatarUrl: ..., // optional
  bio: ..., // optional
};

// Call the `createUserAccount()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await createUserAccount(createUserAccountVars);
// Variables can be defined inline as well.
const { data } = await createUserAccount({ username: ..., email: ..., avatarUrl: ..., bio: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await createUserAccount(dataConnect, createUserAccountVars);

console.log(data.user_insert);

// Or, you can use the `Promise` API.
createUserAccount(createUserAccountVars).then((response) => {
  const data = response.data;
  console.log(data.user_insert);
});
```

### Using `CreateUserAccount`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, createUserAccountRef, CreateUserAccountVariables } from '@dataconnect/generated';

// The `CreateUserAccount` mutation requires an argument of type `CreateUserAccountVariables`:
const createUserAccountVars: CreateUserAccountVariables = {
  username: ..., 
  email: ..., 
  avatarUrl: ..., // optional
  bio: ..., // optional
};

// Call the `createUserAccountRef()` function to get a reference to the mutation.
const ref = createUserAccountRef(createUserAccountVars);
// Variables can be defined inline as well.
const ref = createUserAccountRef({ username: ..., email: ..., avatarUrl: ..., bio: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = createUserAccountRef(dataConnect, createUserAccountVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.user_insert);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.user_insert);
});
```

## CreateNewSandbox
You can execute the `CreateNewSandbox` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
createNewSandbox(vars: CreateNewSandboxVariables): MutationPromise<CreateNewSandboxData, CreateNewSandboxVariables>;

interface CreateNewSandboxRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateNewSandboxVariables): MutationRef<CreateNewSandboxData, CreateNewSandboxVariables>;
}
export const createNewSandboxRef: CreateNewSandboxRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
createNewSandbox(dc: DataConnect, vars: CreateNewSandboxVariables): MutationPromise<CreateNewSandboxData, CreateNewSandboxVariables>;

interface CreateNewSandboxRef {
  ...
  (dc: DataConnect, vars: CreateNewSandboxVariables): MutationRef<CreateNewSandboxData, CreateNewSandboxVariables>;
}
export const createNewSandboxRef: CreateNewSandboxRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the createNewSandboxRef:
```typescript
const name = createNewSandboxRef.operationName;
console.log(name);
```

### Variables
The `CreateNewSandbox` mutation requires an argument of type `CreateNewSandboxVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface CreateNewSandboxVariables {
  title: string;
  description?: string | null;
  themeColor?: string | null;
}
```
### Return Type
Recall that executing the `CreateNewSandbox` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `CreateNewSandboxData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface CreateNewSandboxData {
  sandbox_insert: Sandbox_Key;
}
```
### Using `CreateNewSandbox`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, createNewSandbox, CreateNewSandboxVariables } from '@dataconnect/generated';

// The `CreateNewSandbox` mutation requires an argument of type `CreateNewSandboxVariables`:
const createNewSandboxVars: CreateNewSandboxVariables = {
  title: ..., 
  description: ..., // optional
  themeColor: ..., // optional
};

// Call the `createNewSandbox()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await createNewSandbox(createNewSandboxVars);
// Variables can be defined inline as well.
const { data } = await createNewSandbox({ title: ..., description: ..., themeColor: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await createNewSandbox(dataConnect, createNewSandboxVars);

console.log(data.sandbox_insert);

// Or, you can use the `Promise` API.
createNewSandbox(createNewSandboxVars).then((response) => {
  const data = response.data;
  console.log(data.sandbox_insert);
});
```

### Using `CreateNewSandbox`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, createNewSandboxRef, CreateNewSandboxVariables } from '@dataconnect/generated';

// The `CreateNewSandbox` mutation requires an argument of type `CreateNewSandboxVariables`:
const createNewSandboxVars: CreateNewSandboxVariables = {
  title: ..., 
  description: ..., // optional
  themeColor: ..., // optional
};

// Call the `createNewSandboxRef()` function to get a reference to the mutation.
const ref = createNewSandboxRef(createNewSandboxVars);
// Variables can be defined inline as well.
const ref = createNewSandboxRef({ title: ..., description: ..., themeColor: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = createNewSandboxRef(dataConnect, createNewSandboxVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.sandbox_insert);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.sandbox_insert);
});
```

## AddAssetToSandbox
You can execute the `AddAssetToSandbox` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
addAssetToSandbox(vars: AddAssetToSandboxVariables): MutationPromise<AddAssetToSandboxData, AddAssetToSandboxVariables>;

interface AddAssetToSandboxRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: AddAssetToSandboxVariables): MutationRef<AddAssetToSandboxData, AddAssetToSandboxVariables>;
}
export const addAssetToSandboxRef: AddAssetToSandboxRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
addAssetToSandbox(dc: DataConnect, vars: AddAssetToSandboxVariables): MutationPromise<AddAssetToSandboxData, AddAssetToSandboxVariables>;

interface AddAssetToSandboxRef {
  ...
  (dc: DataConnect, vars: AddAssetToSandboxVariables): MutationRef<AddAssetToSandboxData, AddAssetToSandboxVariables>;
}
export const addAssetToSandboxRef: AddAssetToSandboxRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the addAssetToSandboxRef:
```typescript
const name = addAssetToSandboxRef.operationName;
console.log(name);
```

### Variables
The `AddAssetToSandbox` mutation requires an argument of type `AddAssetToSandboxVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface AddAssetToSandboxVariables {
  sandboxId: UUIDString;
  type: string;
  positionX: number;
  positionY: number;
  content?: string | null;
  label?: string | null;
}
```
### Return Type
Recall that executing the `AddAssetToSandbox` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `AddAssetToSandboxData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface AddAssetToSandboxData {
  asset_insert: Asset_Key;
}
```
### Using `AddAssetToSandbox`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, addAssetToSandbox, AddAssetToSandboxVariables } from '@dataconnect/generated';

// The `AddAssetToSandbox` mutation requires an argument of type `AddAssetToSandboxVariables`:
const addAssetToSandboxVars: AddAssetToSandboxVariables = {
  sandboxId: ..., 
  type: ..., 
  positionX: ..., 
  positionY: ..., 
  content: ..., // optional
  label: ..., // optional
};

// Call the `addAssetToSandbox()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await addAssetToSandbox(addAssetToSandboxVars);
// Variables can be defined inline as well.
const { data } = await addAssetToSandbox({ sandboxId: ..., type: ..., positionX: ..., positionY: ..., content: ..., label: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await addAssetToSandbox(dataConnect, addAssetToSandboxVars);

console.log(data.asset_insert);

// Or, you can use the `Promise` API.
addAssetToSandbox(addAssetToSandboxVars).then((response) => {
  const data = response.data;
  console.log(data.asset_insert);
});
```

### Using `AddAssetToSandbox`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, addAssetToSandboxRef, AddAssetToSandboxVariables } from '@dataconnect/generated';

// The `AddAssetToSandbox` mutation requires an argument of type `AddAssetToSandboxVariables`:
const addAssetToSandboxVars: AddAssetToSandboxVariables = {
  sandboxId: ..., 
  type: ..., 
  positionX: ..., 
  positionY: ..., 
  content: ..., // optional
  label: ..., // optional
};

// Call the `addAssetToSandboxRef()` function to get a reference to the mutation.
const ref = addAssetToSandboxRef(addAssetToSandboxVars);
// Variables can be defined inline as well.
const ref = addAssetToSandboxRef({ sandboxId: ..., type: ..., positionX: ..., positionY: ..., content: ..., label: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = addAssetToSandboxRef(dataConnect, addAssetToSandboxVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.asset_insert);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.asset_insert);
});
```

