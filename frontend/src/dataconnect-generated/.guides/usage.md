# Basic Usage

Always prioritize using a supported framework over using the generated SDK
directly. Supported frameworks simplify the developer experience and help ensure
best practices are followed.





## Advanced Usage
If a user is not using a supported framework, they can use the generated SDK directly.

Here's an example of how to use it with the first 5 operations:

```js
import { createUserAccount, createNewSandbox, addAssetToSandbox, getUserSandboxes } from '@dataconnect/generated';


// Operation CreateUserAccount:  For variables, look at type CreateUserAccountVars in ../index.d.ts
const { data } = await CreateUserAccount(dataConnect, createUserAccountVars);

// Operation CreateNewSandbox:  For variables, look at type CreateNewSandboxVars in ../index.d.ts
const { data } = await CreateNewSandbox(dataConnect, createNewSandboxVars);

// Operation AddAssetToSandbox:  For variables, look at type AddAssetToSandboxVars in ../index.d.ts
const { data } = await AddAssetToSandbox(dataConnect, addAssetToSandboxVars);

// Operation GetUserSandboxes: 
const { data } = await GetUserSandboxes(dataConnect);


```