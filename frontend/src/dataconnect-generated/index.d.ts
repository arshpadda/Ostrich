import { ConnectorConfig, DataConnect, QueryRef, QueryPromise, ExecuteQueryOptions, MutationRef, MutationPromise, DataConnectSettings } from 'firebase/data-connect';

export const connectorConfig: ConnectorConfig;
export const dataConnectSettings: DataConnectSettings;

export type TimestampString = string;
export type UUIDString = string;
export type Int64String = string;
export type DateString = string;




export interface AddAssetToSandboxData {
  asset_insert: Asset_Key;
}

export interface AddAssetToSandboxVariables {
  sandboxId: UUIDString;
  type: string;
  positionX: number;
  positionY: number;
  content?: string | null;
  label?: string | null;
}

export interface Asset_Key {
  id: UUIDString;
  __typename?: 'Asset_Key';
}

export interface Collaborator_Key {
  userId: UUIDString;
  sandboxId: UUIDString;
  __typename?: 'Collaborator_Key';
}

export interface CreateNewSandboxData {
  sandbox_insert: Sandbox_Key;
}

export interface CreateNewSandboxVariables {
  title: string;
  description?: string | null;
  themeColor?: string | null;
}

export interface CreateUserAccountData {
  user_insert: User_Key;
}

export interface CreateUserAccountVariables {
  username: string;
  email: string;
  avatarUrl?: string | null;
  bio?: string | null;
}

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

export interface SandboxActivity_Key {
  id: UUIDString;
  __typename?: 'SandboxActivity_Key';
}

export interface Sandbox_Key {
  id: UUIDString;
  __typename?: 'Sandbox_Key';
}

export interface User_Key {
  id: UUIDString;
  __typename?: 'User_Key';
}

interface CreateUserAccountRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateUserAccountVariables): MutationRef<CreateUserAccountData, CreateUserAccountVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: CreateUserAccountVariables): MutationRef<CreateUserAccountData, CreateUserAccountVariables>;
  operationName: string;
}
export const createUserAccountRef: CreateUserAccountRef;

export function createUserAccount(vars: CreateUserAccountVariables): MutationPromise<CreateUserAccountData, CreateUserAccountVariables>;
export function createUserAccount(dc: DataConnect, vars: CreateUserAccountVariables): MutationPromise<CreateUserAccountData, CreateUserAccountVariables>;

interface CreateNewSandboxRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateNewSandboxVariables): MutationRef<CreateNewSandboxData, CreateNewSandboxVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: CreateNewSandboxVariables): MutationRef<CreateNewSandboxData, CreateNewSandboxVariables>;
  operationName: string;
}
export const createNewSandboxRef: CreateNewSandboxRef;

export function createNewSandbox(vars: CreateNewSandboxVariables): MutationPromise<CreateNewSandboxData, CreateNewSandboxVariables>;
export function createNewSandbox(dc: DataConnect, vars: CreateNewSandboxVariables): MutationPromise<CreateNewSandboxData, CreateNewSandboxVariables>;

interface AddAssetToSandboxRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: AddAssetToSandboxVariables): MutationRef<AddAssetToSandboxData, AddAssetToSandboxVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: AddAssetToSandboxVariables): MutationRef<AddAssetToSandboxData, AddAssetToSandboxVariables>;
  operationName: string;
}
export const addAssetToSandboxRef: AddAssetToSandboxRef;

export function addAssetToSandbox(vars: AddAssetToSandboxVariables): MutationPromise<AddAssetToSandboxData, AddAssetToSandboxVariables>;
export function addAssetToSandbox(dc: DataConnect, vars: AddAssetToSandboxVariables): MutationPromise<AddAssetToSandboxData, AddAssetToSandboxVariables>;

interface GetUserSandboxesRef {
  /* Allow users to create refs without passing in DataConnect */
  (): QueryRef<GetUserSandboxesData, undefined>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect): QueryRef<GetUserSandboxesData, undefined>;
  operationName: string;
}
export const getUserSandboxesRef: GetUserSandboxesRef;

export function getUserSandboxes(options?: ExecuteQueryOptions): QueryPromise<GetUserSandboxesData, undefined>;
export function getUserSandboxes(dc: DataConnect, options?: ExecuteQueryOptions): QueryPromise<GetUserSandboxesData, undefined>;

