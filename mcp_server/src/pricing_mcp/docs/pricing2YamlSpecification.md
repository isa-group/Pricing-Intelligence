# The Pricing2Yaml Syntax

**Pricing2Yaml** (previously known as Yaml4SaaS) emerges as a pragmatic application of the *Pricing4SaaS model*, aligning with the overarching objective of formalizing and structuring pricing information for SaaS platforms. Building upon the foundational principles articulated in *Pricing4SaaS*, Pricing2Yaml embodies a simplified and versatile YAML-based syntax designed for serializing comprehensive details about SaaS offerings. The essence of Pricing2Yaml lies in its capacity to encapsulate pricing plans, add-ons, features and usage limits within a concise and human-readable YAML format. Here is a tempalte specification of the Pricing2Yaml syntax:

```yaml
saasName: GitHub
day: 15
month: 11
year: 2023
currency: USD
hasAnnualPayment: true
features:
  githubPackages:
    description: ...
    valueType: BOOLEAN
    defaultValue: true
    type: DOMAIN
  standardSupport:
    description: ...
    valueType: BOOLEAN
    defaultValue: false
    type: SUPPORT
  #...
usageLimits:
  githubPackagesLimit:
    description: ...
    valueType: NUMERIC
    unit: GB
    defaultValue: 0.5
    linkedFeatures:
      - githubPackages
  #...
plans:
  FREE:
    description: ...
    monthlyPrice: 0
    annualPrice: 0
    unit: "user/month"
  TEAM:
    description: ...
    monthlyPrice: 4
    annualPrice: 3.67
    unit: "user/month"
    features:
      standardSupport:
        value: true
    usageLimits:
      githubPackagesLimit:
        value: 2
  #...
addOns:
  extraGithubPackages:
    availableFor:
      - FREE
      - TEAM
    price: 0.5
    unit: GB/month
    features: null
    usageLimits: null
    usageLimitsExtensions:
      githubPackagesLimit:
        value: 1
  #...
```

Starting with the top-level placeholder, we can describe basic information about the pricing, features, usage limits, plans and add-ons.

**Features** enumerate all the functionalities encompassed in the pricing, classifying them into the types defined in Pricing4SaaS:

- INFORMATION
- INTEGRATION
- DOMAIN
- AUTOMATION
- MANAGEMENT
- GUARANTEE
- SUPPORT
- PAYMENT

detailing each feature's `description`, `valueType` (BOOLEAN, NUMERIC TEXT), and `defaultValue`, whose data type has to be aligned with the `valueType` defined:

- If the `type` is `BOOLEAN`, the `defaultValue` must be a Boolean.
- If the `type` is `NUMERIC`, the `defaultValue` must be Integer or Double
- If the `type` is `TEXT`, the `defaultValue` must be a String.

<!-- Notably, features do not handle NUMERIC values, which are reserved for limits. -->

In addition, depending on each type of feature, the syntax extends expressiveness for each feature type with additional fields:

- For **integration** features, an `IntegrationType` can be specified through the `integrationType` field. If its value is WEB_SAAS, a list of SaaS pricing URLs can be included.
- **Automation** features do also allow to assign theirselves an `AutomationType`.
- For **guarantee** features can reference the corresponding documentation section describing them via the `docURL` field.
- **Payment** features differ from others, requiring values as a list of `PaymentTypes` for standardization.

Similar to features, **UsageLimits** expounds on limitations affecting plans, add-ons, or features in the pricing, tagging each with the corresponding Pricing4SaaS type:

- NON_RENEWABLE
- RENEWABLE
- RESPONSE_DRIVEN
- TIME_DRIVEN

For each limit, similar to features, a `description`, `valueType` (BOOLEAN, TEXT, NUMERIC), and `defaultValue` are provided, accompanied by additional fields such as `unit` or `linkedFeatures`. The latter must be a list of previously described features affected by the limitation.

The **plans** section provides comprehensive details about the distinct pricing plans offered within the SaaS. Each plan is identified by a unique `name`, allowing for easy reference and differentiation. For each one, essential information is specified, including a brief `description`, the `monthlyPrice`, the `annualPrice` (if different from monthly) and the `unit` affected by them, typically expressed as "user/month".

In the `features` and `usageLimits` subsections of each plan, only those requiring a modification in their `defaultValue` should be explicitly listed. For those not mentioned, the `defaultValue` is understood to be equivalent to the `value`.

Within the **addOns** section, the focus is on delineating the specific details of additional offerings beyond the core plans. Each add-on is characterized by its unique features and usage limits, which have to be listed in the structure established in the `features` and `usageLimits` sections, but not included on plans. Similar to the approach taken in the previous section of the file, only those `features` or `usageLimits` necessitating an alteration in the `defaultValue` are explicitly outlined. As an extra field, add-ons also allow to extent a usageLimit. This is extremely powerful for modeling overage cost to some limits.

In conclusion, Pricing2Yaml stands as a practical implementation of the Pricing4SaaS model, providing a YAML-based syntax to formalize SaaS pricing structures in a human-readable format that enhances clarity and simplicity.

---
# Version 2.1

:::info
We use [YAML type](https://yaml.org/type/) abbreviations to describe the supported types of fields.

The YAML snippets demonstrating the Pricing2Yaml specification are intentionally incomplete.
Certain fields have been omitted for clarity and explanation purposes.
:::

## `syntaxVersion`

- **required**
- Supported value: `2.1`

Version of the Pricing2Yaml specification.

```yaml
syntaxVersion: "2.1"
```

## `saasName`

- **required**
- Field type: `str`

Name of the pricing.

```yaml
saasName: "Petclinic"
```

## `version`

- **optional**
- Field type: `string`

Specify the version of the pricing. If the field is not provided with a value, the default is the value of the `createdAt` field as a string

```yaml
version: "jan-25"
```

## `createdAt`

- **required**
- Field type: `timestamp` or `str` in [ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html) format

Date in which your pricing was modeled.

Timestamp:

```yaml
createdAt: 2024-11-14
```

String in ISO 8601:

```yaml
createdAt: "2024-11-14"
```

## `url`

- **optional**
- Field type: a `str` that represents an `URL` must be begin
  with `http` or `https`.

Field `url` holds a URL that points to your pricing page.

```yaml
url: https://example.org/pricing
```

## `variables`

- **optional**
- Field type: `map`

Plan or add-on price can be computed by specifying a expression using variables.
Think of variables as just a convenient way of storing parts of your equation to
reduce the length of plan or add-on expresssion. You can uses variables
in price expressions by prefixing them with a `#`.

Consider the following `yaml` that uses variables in the expression:

```yaml
plans:
  PRO:
    price: 9.99
  ENTERPRISE:
    price: "5 * #x" # 5 * 3
variables:
  x: 3
```

Here `ENTERPRISE` plan uses variable `x` inside of the expression by prefixing it with `#`.
Then variables `x` will be interpolated in the equation so equation will be
`5 * 3` which results in `15.00`.

## `tags`

- **optional**
- Field type: `seq` of `str`

You add one or more features into a group. These groups help features
to be organized when rendering your pricing.

```yaml
tags:
- Code Management
- Code Workflow
- Collaboration
features:
  publicRepositories:
    tag: Code Management
  privateRepositories:
    tag: Code Management
  githubActions:
    tag: Code Workflow
  issues:
    tag: Collaboration
```

## `currency`

- **required**
- Field type: `str`

Currency in which the pricing plans and addOns are selled. Use
preferably [currency codes](https://en.wikipedia.org/wiki/ISO_4217) for
better pricing standarization.

For example `USD` stands for USA dollars and `EUR` stands for Euros.

```yaml
currency: "USD"
```

## `billing`

- **optional**, if a map of billing is not provided `billing` will be set
  by default with:

```yaml
billing:
  monthly: 1
```

- Field type: `map` of `float` inside range `(0..1]`

The prices of plans and add-ons may vary based on the billing option chosen by the user when subscribing.
Longer subscription periods offer greater discounts. `billing` field holds a map
of monthly price reductions to be applied to `price` field of plans and add-ons.
You are free to put inside the map the billing name that you wish.

Price reductions must be positive values greater than 0 and less than or equal to 1.

Consider the following example:

```yaml
billing:
  monthly: 1
  semester: 0.95
  annual: 0.90
plans:
  STANDARD:
    price: 10.00
addOns:
  ULTRA:
    price: 15.00
```

Here `STANDARD` plan costs `10.00` monthly, `9.5` monhtly if billing
by semester and `9.00` monthly if billing annually.
`ULTRA` add-on costs `15.00` monthly if billing monthly, `14.25` monthly if billing by semester and
`13.5` monthly if billing annually.

## `features`

- **required**
- Field type: `map`

A map containing your pricing features. Each key of the map is the feature name and
its value is a map containing feature attributes.

```yaml
features:
  awesome_feature:
  cool_feature:
  nice_feature:
    # ...
```

## `features.<name>.description`

- **optional**
- Field type: `str`

Brief summary of what features does and offers to your users. Feature descriptions
are usually in a collapsable element or in an icon hiding it, see
[Github pricing](https://github.com/pricing) descriptions for example.

```yaml
features:
  publicRepositories:
    description: Host open source projects in public GitHub repositories, accessible via web or command line.
    Public repositories are accessible to anyone at GitHub.com."
```

## `features.<name>.tag`

- **optional**
- Field type: `str`

Name of the group where that feature belongs. First defined a
`tags` block in order to put a field here.

```yaml
tags:
  - Code Management
features:
  publicRepositories:
    tag: Code Management
```

## `features.<name>.type`

- **required**
- Field type: `str`
- Supported values: **one of** `AUTOMATION`, `DOMAIN`, `GUARANTEE`,
  `INFORMATION`, `INTEGRATION`, `MANAGEMENT`, `PAYMENT` or `SUPPORT`

**Automation**: they permit to configure the system in order to perform some actions
autonomously or track thresholds and notify the user if anyone is exceeded.
It also includes any task performed by a bot or AI, such as predictions, generative AI, etc...

```yaml
features:
  codeOwners:
    description:
      Automatically request reviews or require approval by selected contributors
      when changes are made to sections of code that they own.
    type: AUTOMATION
    automationType: TRACKING
```

**Domain**: provide functionality related to the domain of the system,
allowing to perform new operations or using exclusive services.

```yaml
features:
  publicRepositories:
    description:
      Host open source projects in public GitHub repositories, accessible via
      web or command line. Public repositories are accessible to anyone at
      GitHub.com.
    type: DOMAIN
```

**Guarantee**: technical commitments of the company that operates the system towards the users.

```yaml
features:
  dataCypher:
    description: Data encryption at rest and in transit.
    type: GUARANTEE
```

**Information**: allow to see, use, visualize or extract additional data from your features.

```yaml
features:
  auditLogs:
    description:
      Audit logs: Audit logs provide a record of changes and usage in the
      Enterprise Grid plan. You can view audit logs directly in Slack, export
      them in CSV format, and use the audit logs API to create custom monitoring
      tools.
    type: INFORMATION
```

**Integration**: permit users to interact with the system through its API,
or to use functionalities from external third-party software within the system.

```yaml
features:
  adminAnalyticsAPI:
    description: Retrieve analytics data for a specific date in a
      compressed JSON file format.
    type: INTEGRATION
    integrationType: API
```

**Management**: are focused on team leaders and system administrators. They ease
the supervision, organization and guidance of projects, and allow the configuration of
accounts and organization-based restrictions and rules.

```yaml
features:
  customUserGroups:
    description:
      Custom user groups: Facilitate receiving notifications and communicating
      with entire teams, departments, and groups.
    type: MANAGEMENT
```

**Support**: expose the granularity of customer support offered within the plans.

```yaml
features:
  enterpriseSupport:
    description: Custom support for our business partners
    type: SUPPORT
```

**Payment**: specify payment conditions and possibilities.

```yaml
features:
  paymentMethod:
    type: PAYMENT
    defaultValue:
      - INVOICE
      - OTHER
```

## `features.<name>.valueType`

- **required**
- Field type: `str`
- Supported values: **one of** `BOOLEAN`, `NUMERIC` or `TEXT`

Field `valueType` sets the `defaultValue` type signature of the feature you are
modeling. For example, if your feature `valueType` is `BOOLEAN` you must put
`true` or `false` in the `defaultValue` field, if `valueType` is `NUMERIC` you must put
a number and in the case of `TEXT` then `defaultValue` has to be a string or a list of string.

```yaml
features:
  boolean-feature:
    valueType: BOOLEAN
    defaultValue: false
  numeric-feature:
    valueType: NUMERIC
    defaultValue: 0
  text-feature:
    valueType: TEXT
    defaultValue: Pricing2Yaml is awesome!
```

## `features.<name>.defaultValue`

- **required**
- Field type is `bool` if `valueType` is set to `BOOLEAN`
- Field type is `int` if `valueType` set to `NUMERIC`
- Field type is `str` or `seq` of **payment methods** if `valueType` is set to `TEXT`

This field holds the default value of your feature. All default values are shared in your plan and addons. You can
override your features values in `plans.<plan_name>.features` or in `addOns.<addOn_name>.features`
section of your pricing.

Supported **payment methods** are: `CARD`, `GATEWAY`, `INVOICE`, `ACH`, `WIRE_TRANSFER` or `OTHER`.

To help you understand how overriding features works, imagine you have the following pricing
matrix:

|                 | SILVER | GOLD   | PLATINUM |
| --------------- | ------ | ------ | -------- |
| supportPriority | LOW    | MEDIUM | HIGH     |

If you want your `supportPriority` to be different in your `GOLD` and `PLATINUM` plans you
will do the following using Pricing2Yaml syntax:

```yaml
features:
  supportPriority:
    valueType: TEXT
    defaultValue: LOW
plans:
  SILVER:
    features: null
  GOLD:
    features:
      supportPriority:
        value: MEDIUM
  PLATINUM:
    features:
      supportPriority:
        value: HIGH
```

Notice that `SILVER` features are `null`, meaning that, `supportPriority`
will have the value `LOW` as you have previously define it in the `features` block.

## `features.<name>.automationType`

- If feature `type` is `AUTOMATION` this field is **required**
- Field type: `str`
- Supported values: **one of** `BOT`, `FILTERING`, `TRACKING` or `TASK_AUTOMATION`

Type of the automation feature.

**BOT**: every automation feature that depends on machine learning algorithms or LLMs.

```yaml
features:
  postbot:
    description: "https://learning.postman.com/docs/getting-started/basics/about-postbot/"
    type: AUTOMATION
    automationType: BOT
```

**FILTERING**: every automation feature that filters information. For example, spam filtering
of mail clients.

```yaml
features:
  emailSpamFilter:
    description: "Help protect your business against spam and malware with cloud-based email filtering"
    type: AUTOMATION
    automationType: FILTERING
```

**TRACKING**: every automation feature that monitors a metric and notify the user
when reaching his threshold. For example, features that triggers some kind of event
in the system like reaching the limit of API calls.

```yaml
features:
  dependabotAlerts:
    description: "Get notified when there are new vulnerabilities affecting dependencies in your repositories."
    type: AUTOMATION
    automationType: TRACKING
```

**TASK_AUTOMATION**: every automation feature that permit users to automate tasks. For example,
automatically moving the issues to "Done" when thery are closed in the Github kanban board.

```yaml
features:
  dependabotVersionUpdates:
    description: "Keep projects up-to-date by automatically opening pull requests that update out-of-date dependencies."
    type: AUTOMATION
    automationType: TASK_AUTOMATION
```

## `features.<name>.docUrl`

- If feature `type` is `GUARANTEE` this is **required**
- Field type: `str`

URL redirecting to the guarantee or compliance documentation.

```yaml
features:
  enterpriseGradeSecurity:
    description: "https://www.wrike.com/features/admin-security/"
    type: GUARANTEE
    docUrl: "https://www.wrike.com/features/admin-security/"
```

## `features.<name>.integrationType`

- If feature `type` is `INTEGRATION` this is **required**
- Field type: `str`
- Supported values: **one of** `API`, `EXTENSION`, `IDENTITY_PROVIDER`, `WEB_SAAS`, `MARKETPLACE` or `EXTERNAL_DEVICE`

Type of the integration feature.

**API**: every feature that includes an internal API that developers can consume.

```yaml
adminAnalyticsAPI:
  description: "Admin analytics API: Retrieve analytics data for a specific date in a compressed JSON file format."
  type: INTEGRATION
  integrationType: API
```

**EXTENSION**: every integration feature that extends your SaaS using an external system. For example a browser extension
or code editor extension like VSCode.

```yaml
features:
  copilotIDEIntegration:
    description: "Get IDE integration from Copilot in your IDE and mobile devices."
    type: INTEGRATION
    integrationType: EXTENSION
```

**IDENTITY_PROVIDER**: every integration feature, that involves a process to authenticate users
internally or externally. For example Single Sign On (SSO) or LDAP.

```yaml
features:
  ldap:
    description: Access GitHub Enterprise Server using your existing accounts and centrally manage repository access.
    type: INTEGRATION
    integrationType: IDENTITY_PROVIDER
```

**WEB_SAAS**: every integration feature that involves an external SaaS. For example,
sync your calendar with Outlook. Usage of `features.<name>.pricingUrls` is required.

```yaml
features:
  githubIntegration:
    description: "Link your Overleaf projects directly to a GitHub repository that
    acts as a remote repository for your overleaf project. This allows you to
    share with collaborators outside of Overleaf, and integrate Overleaf into more complex workflows."
    type: INTEGRATION
    integrationType: WEB_SAAS
    pricingsUrls:
      - https://github.com/pricing
```

**MARKETPLACE**: every integration feature that offers many posibilities to integrate with other systems.
For example a marketplace that offers widgets.

```yaml
features:
  githubApps:
    description: Install apps that integrate directly with GitHub's API to improve
    development workflows or build your own for private use or publication in the GitHub Marketplace."
    type: INTEGRATION
    integrationType: MARKETPLACE
```

**EXTERNAL_DEVICE**: every integration feature that involves interactiing with an outer device, like
a mobile, a computer desktop. For example a 2FA feature.

```yaml
features:
  apps:
    description: "Track time using a mobile app, desktop app, and browser extension."
    type: INTEGRATION
    integrationType: EXTERNAL_DEVICE
```

## `features.<name>.pricingUrls`

- If feature `type` is `INTEGRATION` and `integrationType` is `WEB_SAAS` this field is **required**
- Field type: `seq` of `str`

You can specify a list of URLs linking to the associated pricing page of
third party integrations that you offer in your pricing.

```yaml
features:
  googleWorkspaceIntegration:
    type: INTEGRATION
    integrationType: WEB_SAAS
    pricingURLs:
      - https://workspace.google.com/pricing
```

## `features.<name>.render`

- **optional**
- Field type: one of `AUTO`, `DISABLED`, `ENABLED`

Choose the behaviour when displaying the feature of the pricing. Use this
feature in the Pricing2Yaml editor.

```yaml
features:
  googleWorkspaceIntegration:
    render: DISABLED
```

## `usageLimits`

- **optional**
- Field type: `map`

A map containing the usage limits of your pricing. Each entry of this map
will be the name of the corresponding usage limit.

```yaml
usageLimits:
  maxPets:
  collaborators:
  githubActionsQuota:
    # ...
```

## `usageLimits.<name>.description`

- **optional**
- Field type: `str`

Brief summary of what the usage limit restricts.

```yaml
usageLimits:
  useMessagesAccess:
    description: "The number of days you can access message and file information."
```

## `usageLimits.<name>.type`

- **required**
- Field type: `str`
- Supported values: **one of** `NON_RENEWABLE`
  `RENEWABLE` , `RESPONSE_DRIVEN` or `TIME_DRIVEN`

Field that indicates the type of usage limit based on our clasification of usage limits.

**NON_RENEWABLE**: define a static limit towards which the user approaches, and that will
remain until the end of the subscription.

```yaml
usageLimits:
  uploadSizeLimit:
    type: NON_RENEWABLE
```

**RENEWABLE**: their limit is reset after a period of time, could be a day, week, month...

```yaml
usageLimits:
  githubCodepacesCoreHours:
    type: RENEWABLE
```

**RESPONSE_DRIVEN**: represent a limit where user consumes more or less of his quota depending
on the computational cost of the SaaS associated with the request.

```yaml
usageLimits:
  flowCredits:
    description: "Number of flows executions steps included per month"
    unit: credit/month
    type: RESPONSE_DRIVEN
```

**TIME_DRIVEN**: with this type the quota is consumed by usage time, and is normally
combined with a non-renewable limit.

```yaml
compileTimeoutLimit:
  description:
    This is how much time you get to compile your project on the Overleaf servers.
    You may need additional time for longer or more complex projects.
  type: TIME_DRIVEN
```

## `usageLimits.<name>.valueType`

- **required**
- Field type: `str`
- Supported values: **one of** `BOOLEAN`, `NUMERIC` or `TEXT`

Field `valueType` sets the `defaultValue` type signature of the usage limit you are
modeling. For example, if your usage limit `valueType` is `BOOLEAN` you must put
`true` or `false` in the `defaultValue` field, if `valueType` is `NUMERIC` you must put
a number and in the case of `TEXT` then `defaultValue` has to be a string.

```yaml
usageLimits:
  privateAccessToCodeRepositories:
    valueType: BOOLEAN
    defaultValue: false
  storageQuota:
    valueType: NUMERIC
    defaultValue: 30
  support:
    valueType: TEXT
    defaultValue: LOW
```

## `usageLimits.<name>.defaultValue`

- **required**
- Field type is `bool` if `valueType` is set to `BOOLEAN`
- Field type is `int` if `valueType` set to `NUMERIC`
- Field type is `str` if `valueType` is set to `TEXT`

This field holds the default value of your usage limit. All default values are shared in your plan and addons. You can
override your usage limits values in `plans.<plan_name>.usageLimits` or in `addOns.<addOn_name>.usageLimits`
section of your pricing.

To help you understand how overriding usage limits works, imagine you have the following pricing
matrix:

|               | SILVER | GOLD | PLATINUM |
| ------------- | ------ | ---- | -------- |
| collaborators | 1      | 6    | 10       |

If you want your `collaborators` usage limit to be different in your `GOLD` and `PLATINUM` plans you
will do the following using Pricing2Yaml syntax:

```yaml
usageLimits:
  collaborators:
    valueType: NUMERIC
    defaultValue: 1
plans:
  SILVER:
    usageLimits: null
  GOLD:
    usageLimits:
      collaborators:
        value: 6
  PLATINUM:
    usageLimits:
      collaborators:
        value: 10
```

## `usageLimits.<name>.unit`

- **required**
- Field type: `str`

Measure of the usage limit.

Here is an example using unit from Github pricing:

```yaml
usageLimits:
  githubActionsQuota:
    unit: minute/month
```

## `usageLimits.<name>.linkedFeatures`

- **optional**
- Field type: `seq` of feature names which are `str`

Bounds your usage limit to a one or multiple features by adding your
feature name to the list.

```yaml
features:
  feature1:
  feature2:
  feature3:
  feature4:
usageLimits:
  usageLimit1:
    linkedFeatures:
      - feature1
      - feature2
      - feature3
  usageLimit2:
    linkedFeatures:
      - feature4
```

## `usageLimits.<name>.render`

- **optional**
- Field type: one of `AUTO`, `DISABLED`, `ENABLED`

Choose the behaviour when displaying the usage limit of the pricing. Use this
feature in the Pricing2Yaml editor.

```yaml
usageLimits:
  usageLimit1:
    render: DISABLED
```

## `plans`

- **optional**
- Field type: `map`

A map containing the plans of your pricing. Each entry of this map
will be the name of the corresponding plan.

```yaml
saasName: Petclinic
plans:
  BASIC:
  GOLD:
  PLATINUM:
  # ...
```

:::info
You have to specify at least `plans` or `addOns`. A combination
of both also works.
:::

## `plans.<name>.description`

- **optional**
- Field type: `str`

An overview describing the plan's purpose.

```yaml
plans:
  FREE:
    description: "All the basics for businesses that are just getting started."
```

## `plans.<name>.private`

- **optional**
- Field type: `bool`, if not provided `private` is `false` by default

Flag that indicates wheter your plan should be displayed to the public.

Companies can contact the SaaS sales team to negotiate custom features or usage limits.
Enable the `private` field to store the plan configuration without making it visible to your users:

```yaml
features:
  feature1:
    defaultValue: true
usageLimits:
  usageLimit1:
    defautlValue: 30
    linkedFeatures:
      - feature1
plans:
  ENTERPRISE:
    private: false
    price: 29.99
  JOHN-DOE-CUSTOM-ENTERPRISE-PLAN:
    private: true
    price: 39.99
    usageLimits:
      usageLimit1:
        value: 100
```

## `plans.<name>.price`

- **required**
- Field type: `float` or `str` formated as a SpEL

Price of your plan when billing monthly.

```yaml
plans:
  PRO:
    price: 14.99
addOns:
  BOOSTER:
    price: 17.99
```

**Price mathematical expression**

Put in the root of the specification a field named `variables`.
To define custom variables inside this map put a key with the corresponding
value. To use the defined variable inside the [SpEL](https://docs.spring.io/spring-framework/reference/core/expressions.html)
expression, prefix the name of the key with a `#`.

```yaml
plans:
  PRO:
    price: "#x * #y" # SpEL evaluates to: 30.0
addOns:
  EXTRA_REQUESTS:
    price: "10 + #z" # SpEL evaluates to: 10.4
variables:
  x: 15.00
  y: 2.0
  z: 0.4
```

Key names in this map should be alphanumeric, i.e, from a to z or A to Z
or a number from 0 to 9, a key should not start with a number. Allowed variables names
correspond to the following regex expression `^[a-zA-Z][a-zA-Z0-9]*$`.

```yaml
# Good naming
x: 4
foo: 0
f00: 0
b4r: 0
fooBar:

# Bad naming
"#foo": 0
foo_bar: 0
foo/bar: 0
0foo: 0
```

Supported values for variables are `int`, `float` and `bool`.

```yaml
# Supported values
myIntegerValue: 5
myFloatValue: 5.0
myBooleanVariable: true

# Unsupported values
myNullValue: null
defaultsToNullValue:
myStringVariable: Hello world!
myDateVariable: 2024-12-03
```

## `plans.<name>.unit`

- **required**
- Field type: `str`

Measure of the plan subscription.

```yaml
plans:
  TEAM:
    unit: user/month
```

## `plans.<name>.features`

- **optional** when leaving the field blank or `null`, loads every `defaultValue` of your features
- Field type: `map`

A map containing the keys of your features you want to override.

```yaml
features:
  awesome_feature:
  cool_feature:
  nice_feature:
plans:
  my_plan:
    features:
      cool_feature:
      nice_feature:
        # ...
```

## `plans.<name>.features.<name>.value`

- **optional**
- Field type: `bool`, `int` or `str` depending on the `valueType` of the feature

Every plan that you model will have by default all features `defaultValue`. You
can customize it by putting a value in it.

```yaml
features:
  supportPriority:
    defaultValue: LOW
plans:
  GOLD:
    features:
      supportPriority:
        value: MEDIUM
```

## `plans.<name>.usageLimits`

- **optional** when leaving the field blank or `null` it loads every `defaultValue` of your usage limits
- Field type: `map`

A map containing the keys of your usage limits you want to override.

```yaml
usageLimits:
  usageLimit1:
  usageLimit2:
plans:
  my_plan:
    usageLimits:
      usageLimit1:
      usageLimit2:
        # ...
```

## `plans.<name>.usageLimits.<name>.value`

- **optional**
- Field type: `bool`, `int` or `str` depending on the `valueType` of the usage limit

Every plan that you model will have by default all usage limits `defaultValue`. You
can customize it by putting a value in it.

In the following example `collaborators` usage limit is overridden by `STANDARD`.

```yaml
usageLimits:
  collaborators:
    defaultValue: 1
addOns:
  STANDARD:
    usageLimits:
      collaborators:
        value: 6
```

## `addOns`

- **optional**
- Field type: `map`

A map containing the addons of your pricing. Each entry of this map
will be the name of the corresponding addon.

```yaml
addOns:
  awesome_addOn:
  cool_addOn:
    # ...
```

:::info
You have to specify at least `plans` or `addOns`. A combination
of both also works.
:::

## `addOns.<name>.description`

- **optional**
- Field type: `str`-

An overview describing the addon purpose.

```yaml
addOns:
  StorageBooster:
    description: Boost your file storage. Do not run out of space!.
```

## `addOns.<name>.availableFor`

- **optional**, if the `availableFor` field is not present within an add-on,
  it will be available for all plans by default
- Field type: `seq` of plan names

This add-on fields indicates that your add-on is available to purchase only if
the user is subscribed to any of the plans indicated in this list.

```yaml
plans:
  SILVER:
  GOLD:
  PLATINUM:
    # ...
addOns:
  EMERALD:
    # if availableFor is missing or null EMERALD is available for
    # SILVER, GOLD and PLATINUM by default
    # availableFor: null
  RUBY:
    availableFor:
      - GOLD
      - SILVER
```

## `addOns.<name>.private`

- **optional**
- Field type: `bool`, if not provided `private` is `false` by default

Flag that indicates wheter your add-on should be displayed to the public.

Companies can contact the SaaS sales team to negotiate custom features or usage limits.
Enable the `private` field to store the add-on configuration without making it visible to your users:

```yaml
features:
  feature1:
    defaultValue: false
usageLimits:
  usageLimit1:
    defautlValue: 10
    linkedFeatures:
      - feature1
addOns:
  ENTERPRISE-ADDON:
    private: false
    price: 9.99
    features:
      feature1:
        value: true
  JOHN-DOE-CUSTOM-ADDON:
    private: true
    price: 14.99
    features:
      feature1:
        value: true
    usageLimits:
      usageLimit1:
        value: 30
```

## `addOns.<name>.dependsOn`

- **optional**
- Field type: `seq` of addon names

A list of addon to be subscribed in order to purchase the current addon.

Imagine that your addon `SECURITY` depends on `ENTERPRISE` addon. That
means that in order to include in your subscription the `SECURITY` addon you also have to include
`ENTERPRISE` addon.

That way you can subscribe to `ENTERPRISE` or `ENTERPRISE` and `SECURITY` but no exclusively to
`SECURITY` addon.

```yaml
addOns:
  ENTERPRISE:
  SECURITY:
    dependsOn:
      - ENTERPRISE
```

## `addOns.<name>.excludes`

In the current add-on that you are defining specify one or more add-ons that cannot be purchased
together.

In this example we have two addOns available for plan `BASIC` that are `addOnA` and `addOnB`.
Since `addOnA` excludes `addOnB` purchasing plan `BASIC`, `addOnA` and `addOnB` is not posible.
It is valid to purchase `BASIC` and `addOnA` and `BASIC` and `addOnB`.

```yaml
plans:
  BASIC:
addOns:
  addOnA:
    availableFor:
      - BASIC
    excludes:
      - addOnB
  addOnB:
    availableFor:
      - BASIC
```

## `addOns.<name>.price`

- **required**
- Field type: `float` or `str` formated as a SpEL

Price of your add-on' when billing monthly.

```yaml
plans:
  PRO:
    price: 14.99
addOns:
  BOOSTER:
    price: 17.99
```

**Price mathematical expression**

Put in the root of the specification a field named `variables`.
To define custom variables inside this map put a key with the corresponding
value. To use the defined variable inside the [SpEL](https://docs.spring.io/spring-framework/reference/core/expressions.html)
expression, prefix the name of the key with a `#`.

```yaml
plans:
  PRO:
    price: "#x * #y" # SpEL evaluates to: 30.0
addOns:
  EXTRA_REQUESTS:
    price: "10 + #z" # SpEL evaluates to: 10.4
variables:
  x: 15.00
  y: 2.0
  z: 0.4
```

Key names in this map should be alphanumeric, i.e, from a to z or A to Z
or a number from 0 to 9, a key should not start with a number. Allowed variables names
correspond to the following regex expression `^[a-zA-Z][a-zA-Z0-9]*$`.

```yaml
# Good naming
x: 4
foo: 0
f00: 0
b4r: 0
fooBar:

# Bad naming
"#foo": 0
foo_bar: 0
foo/bar: 0
0foo: 0
```

Supported values for variables are `int`, `float` and `bool`.

```yaml
# Supported values
myIntegerValue: 5
myFloatValue: 5.0
myBooleanVariable: true

# Unsupported values
myNullValue: null
defaultsToNullValue:
myStringVariable: Hello world!
myDateVariable: 2024-12-03
```

## `addOns.<name>.unit`

- **required**
- Field type: `str`

Measure of the addon subscription.

```yaml
addOns:
  gitLFSDataPack:
    unit: user/month
```

## `addOns.<name>.features`

- **optional** when leaving the field blank or `null`, loads every `defaultValue` of your features
- Field type: `map`

A map containing the keys of your features you want to override.

```yaml
features:
  awesome_feature:
  cool_feature:
  nice_feature:
addOns:
  my_addOn:
    features:
      cool_feature:
      nice_feature:
        # ...
```

## `addOns.<name>.features.<name>.value`

- **optional**
- Field type: `bool`, `int` or `str` depending on the `valueType` of the feature

Every addon that you model will have by default all features `defaultValue`. You
can customize it by putting a value in it.

```yaml
features:
  supportPriority:
    defaultValue: LOW
addOns:
  B:
    features:
      supportPriority:
        value: MEDIUM
```

## `addOns.<name>.usageLimits`

- **optional** when leaving the field blank or `null` it loads every `defaultValue` of your usage limits
- Field type: `map`

A map containing the keys of your usage limits you want to override.

```yaml
usageLimits:
  usageLimit1:
  usageLimit2:
addOns:
  my_addOn:
    usageLimits:
      usageLimit1:
      usageLimit2:
        # ...
```

## `addOns.<name>.usageLimits.<name>.value`

- **optional**
- Field type: `bool`, `int` or `str` depending on the `valueType` of the usage limit

Every addon that you model will have by default all usage limits `defaultValue`. You
can customize it by putting a value in it.

In the following example `collaborators` usage limit are overridden by `B` and `C`:

```yaml
usageLimits:
  collaborators:
    defaultValue: 1
addOns:
  A:
    usageLimits: null
  B:
    usageLimits:
      collaborators:
        value: 6
  C:
    usageLimits:
      collaborators:
        value: 10
```

## `addOns.<name>.usageLimitsExtensions`

- **optional**
- Field type: `map`

A map containing the keys of your usage limits that you want to extend with this addon.

```yaml
usageLimits:
  my_usage_limit:
    defaultValue: 5
addOns:
  my_addOn:
    usageLimitsExtensions:
      my_usage_limit:
```

## `addOns.<name>.usageLimitsExtensions.<name>.value`

- **optional**
- Field type: `bool`, `int` or `str` depending on the `valueType` of the usage limit

Specify the quantity in which you want to extend your usage limit

In the following example `collaborators` usage limit is extended by 10 units:

```yaml
usageLimits:
  collaborators:
    defaultValue: 1
addOns:
  B:
    usageLimitsExtensions:
      collaborators:
        value: 10
```

---

# Modeling good practices

## Use defensive pricing techniques

When it comes to modelling in `Pricing2Yaml` you are going to have several `NUMERIC`
usage limits linked to `BOOLEAN` features. You should be carefull when setting
their `defaultValue` as it can affect the feature evaluation.

:::info Terminology

- A **feature** is considered **enabled** if its `defaultValue` is `true`
- A **feature** is **disabled** if its `defaultValue` is `false`
- An **usage limit** is **enabled** if its `defaultValue` is greater than `0`
- An **usage limit** is **disabled** if its `defaultValue` is `0`
:::

**TLDR**:

- If a usage limit is linked to only **one feature** both should be enabled or disabled.
- An usage limit linked to multiple feature does not follow this rule.

### Example

Good practice:

```yaml
features:
  featureA:
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: false
  featureB:
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: true
usageLimits:
  featureALimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 0
    linkedFeatures:
    - featureA
  featureBLimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 30
    linkedFeatures:
    - featureB
```

Bad practice:

```yaml
features:
  featureA:
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: false
  featureB:
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: true
usageLimits:
  featureALimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 30
    linkedFeatures:
    - featureA
  featureBLimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 0
    linkedFeatures:
    - featureB
```

:::warning Feature and usage limit inconsistencies

When it comes to modelling the following inconsistencies can happen:

- A feature is enabled and its linked usage limit is disabled
- A feature is disabled and its linked usage limit is disabled

### Feature is enabled and usage limit is disabled

```yaml
features:
  featureA:
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: true
usageLimits:
  featureALimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 0
    linkedFeatures:
    - featureA
```

### Feature is disabled and usage limit is enabled

```yaml
features:
  featureB:
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: false
usageLimits:
  featureBLimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 30
    linkedFeatures:
    - featureB
```

:::

### A story about bad modelling

The business ACME has a SaaS and they are planning to release an extra feature that enable users
to store files in the cloud. They have stablished the following usage restrictions:

|              |    Free      | Professional | Enterprise |
|--------------|--------------|--------------|------------|
| Data Storage | Not Included | 50 GB        | 200 GB     |

ACME is using `Pricing2Yaml` to model his pricing and they have included the file storage
feature like the following:

```yaml
features:
  # other features
  fileStorage:
    description: Keep your files securely stored, up to date, and accessible across devices
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: false
    expression: userContext['currStorage'] < planContext['usageLimits']['dataStorageLimit']
usageLimits:
  fileStorageLimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 50
    unit: GB
    linkedFeatures:
    - fileStorage
plans:
  FREE:
    features: null
    usageLimits: null
  PROFESSIONAL:
    features:
      fileStorage:
        value: true
    usageLimits: null
  ENTERPRISE:
    features:
      fileStorage:
        value: true
    usageLimits:
      fileStorageLimit:
        value: 200
```

As explained in the [Pricing2Yaml syntax](pricing2yaml-v21-specification.mdx) section
all plans will inherit global features and usage limits `defaultValue` resulting in the
following interpreted values when parsing the config file:

|                    |    Free      | Professional | Enterprise |
|--------------------|--------------|--------------|------------|
| `fileStorage`      | false | true  | true     |
| `fileStorageLimit` | 50 | 50 |  200  |

The feature looks promissing and ACME decides to ship the feature. Months later,
they decide to **enable file storage** feature to **FREE** users after doing some analysis
on their data.

The developer in charge of mantaining the configuration file **enables** the
file storge feature **globally**, but **forgets** to update **global file storage limit**.

Here is the config file with the modification:

```yaml
features:
  fileStorage:
    description: Keep your files securely stored, up to date, and accessible across devices
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: true
    expression: userContext['currStorage'] < planContext['usageLimits']['dataStorageLimit']
usageLimits:
  fileStorageLimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 50
    unit: GB
    linkedFeatures:
    - fileStorage
plans:
  FREE:
    features: null
    usageLimits: null
  PROFESSIONAL:
    usageLimits: null
  ENTERPRISE:
    usageLimits:
      fileStorageLimit:
        value: 200
```

Plans will inherit the following values from the configuration file:

|                    |    Free      | Professional | Enterprise |
|--------------------|--------------|--------------|------------|
| `fileStorage`      | true | true  | true     |
| `fileStorageLimit` | 50 | 50 |  200  |

A week later the development team finds out that FREE users were storing an unusual
amount of files and servers run out of disk space quickly. They tracked
what went wrong and discover that `fileStorageLimit` was too high, so they change
it accordinly.

```yaml
features:
  fileStorage:
    description: Keep your files securely stored, up to date, and accessible across devices
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: true
    expression: userContext['currStorage'] < planContext['usageLimits']['dataStorageLimit']
usageLimits:
  fileStorageLimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 5
    unit: GB
    linkedFeatures:
    - fileStorage
plans:
  FREE:
    features: null
    usageLimits: null
  PROFESSIONAL:
    // highlight-start
    usageLimits:
      fileStorageLimit:
        value: 50
    // highlight-end
  ENTERPRISE:
    usageLimits:
      fileStorageLimit:
        value: 200
```

Plans will inherit the following values from the configuration file:

|                    |    Free      | Professional | Enterprise |
|--------------------|--------------|--------------|------------|
| `fileStorage`      | true | true  | true     |
| `fileStorageLimit` | 5 | 50 |  200  |

If they originally modeled the pricing with an usage limit of 0 GB, FREE
users would not be able to store any file after enabling `fileStorage` globally
and servers would not run out of space:

```yaml
features:
  # other features
  fileStorage:
    description: Keep your files securely stored, up to date, and accessible across devices
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: false
    expression: userContext['currStorage'] < planContext['usageLimits']['dataStorageLimit']
usageLimits:
  fileStorageLimit:
    valueType: NUMERIC
    // highlight-next-line
    defaultValue: 0
    unit: GB
    linkedFeatures:
    - fileStorage
plans:
  FREE:
    features: null
    usageLimits: null
  PROFESSIONAL:
    features:
      fileStorage:
        value: true
    usageLimits:
      fileStorageLimit:
        value: 50
  ENTERPRISE:
    features:
      fileStorage:
        value: true
    usageLimits:
      fileStorageLimit:
        value: 200
```

## Tag your features

If your pricing has a lot of features your potential users might
have trouble to mentally process them all at once. This could lead the user
to leave your page and choose another competitor due to the lack of structure of the
pricing.

To information saturatin group related features with `tags`. Your users will see the features
grouped by chunks small amounts, making the pricing easier to recall.
This technique is known in psychology as [chunking](https://en.wikipedia.org/wiki/Chunking_(psychology)).

Here are some SaaS providers using this technique:

[Mailchimp](https://mailchimp.com/pricing/marketing/compare-plans):

![Mailchimp tags](../../static/img/tags-mailchimp.png)

[Salesforce](https://www.salesforce.com/sales/pricing/):

![Mailchimp tags](../../static/img/tags-salesforce.png)

[Slack](https://slack.com/pricing):

![Mailchimp tags](../../static/img/tags-slack.png)

### Example

Good practice:

```yaml
syntaxVersion: '2.1'
saasName: Databox
url: https://web.archive.org/web/20250304080336/https://databox.com/pricing
tags:
- Data Collection
- Connect any Data Source
- Account management & security
features:
  dataSources:
    tag: Data Collection
  dataSyncFrequency:
    tag: Data Collection
  historicalData:
    tag: Data Collection
  warehouseDataStorage:
    tag: Data Collection
  databoxIntegrations:
    tag: Connect any Data Source
  thirdPartyIntegrations:
    tag: Connect any Data Source
    integrationType: MARKETPLACE
  pushCustomDataToAPI:
    tag: Connect any Data Source
  customApiIntegrations:
    tag: Connect any Data Source
  sqlIntegrations:
    tag: Connect any Data Source
  spreadsheetsIntegration:
    tag: Connect any Data Source
  userManagement:
    type: Account management & security
  twoFactorAuthentication:
    tag: Account management & security
  singleSignOn:
    tag: Account management & security
  advancedSecurityManagement:
    tag: Account management & security
```

Bad practice

```yaml
syntaxVersion: '2.1'
saasName: Databox
url: https://web.archive.org/web/20250304080336/https://databox.com/pricing
features:
  dataSources:
  dataSyncFrequency:
  historicalData:
  warehouseDataStorage:
  databoxIntegrations:
  thirdPartyIntegrations:
  pushCustomDataToAPI:
  customApiIntegrations:
  sqlIntegrations:
  spreadsheetsIntegration:
  userManagement:
  twoFactorAuthentication:
  singleSignOn:
  advancedSecurityManagement:
   ## ..
```

## Use usage limits naming conventions

It is a good habit to name usage limits including part of the feature name that is linked,
for example:

- `<featureName>Limit`
- `<featureName>Uses`
- `<featureName>Cap`


### Example

Good practice:

```yaml
features:
  //highlight-next-line
  workspaces:
    valueType: BOOLEAN
    defaultValue: true
usageLimits:
  // highlight-next-line
  workspacesLimit:
    description: The number of workspaces you can use.
    valueType: NUMERIC
    defaultValue: 1
    unit: workspace
    type: NON_RENEWABLE
    linkedFeatures:
    - workspaces
```

Bad practice:

```yaml
features:
  //highlight-next-line
  workspaces:
    valueType: BOOLEAN
    defaultValue: true
usageLimits:
// highlight-next-line
  usageLimitWk:
    description: The number of workspaces you can use.
    valueType: NUMERIC
    defaultValue: 1
    unit: workspace
    type: NON_RENEWABLE
    linkedFeatures:
    - workspaces
```

## Provide descriptions

When modeling features, we tend to reduce the length of the name by identifying
it with a few keywords. However, understanding the functionality only looking at
the name can be a difficult task and subject to interpretation.

In cases where further context is greatly appreciated, write a brief summary of
the description in the `description` field. That way, users will be able to
understand your feature even better. As always, decide when it is
necessary to provide a little more context.

### Example

Here is an example extracted from [Databox](https://databox.com/pricing):

![Databox description](../../static/img/databox-description.png)

Good practice:

```yaml
features:
  dataCalculations:
    // highlight-start
    description: | 
      Easily calculate (add, subtract, multiply, divide) new metrics
      from any Data Source using Data Calculations.
    // highlight-end
    valueType: BOOLEAN
    defaultValue: true
    type: DOMAIN
```

Bad practice:

```yaml
features:
  dataCalculations:
    # What calculation are performed?
    valueType: BOOLEAN
    defaultValue: true
    type: DOMAIN
```

## Avoid using TEXT valueType

In 99.9% of total cases a pricing can be modeled with `BOOLEAN` features
and `NUMERIC` usage limits, but when `BOOLEAN` and `NUMERIC` `valueType`
are not enough you can use `TEXT` as a last resource. You should use `BOOLEAN`
and `NUMERIC` as much as possible.

### Example

Take a look at Search engine indexing (SEO) feature in [Notion](https://www.notion.com/pricing) pricing:

![Stacked features](../../static/img/stacked-features.png)

You could be tempted to model this as a `TEXT` feature, but there is another option that uses
`BOOLEAN` features. In this case we can model this feature as two `BOOLEAN` features,
`basicSearchEngineIndexing` and `advancedSearchEngineIndexing`. `basicSearchEngineIndexing` is
available for all plans and `advancedSearchEngineIndexing` is only available for Plus, Business and
Enterprise plans.

Good practice:

```yaml
features:
  // highlight-start
  basicSearchEngineIndexing:
    valueType: BOOLEAN
    defaultValue: true
  advancedSearchEngineIndexing:
    valueType: BOOLEAN
    defaultValue: false
  // highlight-end
plans:
  FREE:
    features: null
  PLUS:
    features:
      advancedSearchEngineIndexing:
        value: true
  BUSINESS:
    features:
      advancedSearchEngineIndexing:
        value: true
  ENTERPRISE:
    features:
      advancedSearchEngineIndexing:
        value: true
```

Bad practice

```yaml
features:
  // highlight-start
  searchEngineIndexing:
    valueType: TEXT
    defaultValue: Basic
  // highlight-end
plans:
  FREE:
    features: null
  PLUS:
    features:
      advancedSearchEngineIndexing:
        value: Advanced
  BUSINESS:
    features:
      advancedSearchEngineIndexing:
        value: Advanced
  ENTERPRISE:
    features:
      advancedSearchEngineIndexing:
        value: Advanced
```

## Avoid modelling trials

You might be tempted to model trial features or demos but in reality
those features are not granting users permanent access. In practice
if a feature is available for trial or a preview of it, that feature should not
be enabled for that particular plan.

Example from [Notion](https://www.notion.com/pricing) pricing:

![Notion](../../static/img/limited-trial.png)


### Example

Example from [Mailchimp](https://mailchimp.com/pricing/marketing/compare-plans/):

![Mailchimp](../../static/img/preview-mailchimp.png)

Good practice:

Customer Journey Builder has a free preview for Free plan, that feature is `false` by default even if the pricing offers a preview.

```yaml
features:
  customerJourneyBuilder:
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: false
plans:
  FREE:
    features: null
  ESSENTIALS:
    features:
      customerJourneyBuilder:
        value: true
  STANDARD:
    features:
      customerJourneyBuilder:
        value: true
  PREMIUM:
    features:
      customerJourneyBuilder:
        value: true
```

Bad practice:

Here security alerts is enabled for all plans permanently, but we only want FREE users
to use it temporarily. Disabling that feature is highly recommended.

```yaml
features:
  customerJourneyBuilder:
    valueType: BOOLEAN
    // highlight-next-line
    defaultValue: true
plans:
  FREE:
    features: null
  ESSENTIALS:
    features: null
  STANDARD:
    features: null
  PREMIUM:
    features: null
```

## Avoid modelling recommended usage limits

Saas providers instead of restricting a feature for a particular plan, they make
a suggestion for the ideal usage limit. These recommended users limit must not
be modeled since there is no restriction for that feature.

Example extracted from [Crowdcast](https://www.crowdcast.io/pricing) pricing:

![Recommend user limits](../../static/img/recommended-users.png)

### Example

|                    |    Free      | Professional | Enterprise |
|--------------------|--------------|--------------|------------|
| Online text editor experience     | Ideal for 1-3 concurrent users | Ideal for 5+ concurrent users  |  Ideal for 15+ concurrent users    |

Good practice:

```yaml
features:
  onlineTextEditor:
    valueType: BOOLEAN
    defaultValue: true
plans:
  FREE:
  PROFESSIONAL:
  ENTERPRISE:
    # .. Not modeled recommended usage limits present
```

Bad practice:

You should not model recommended usage limits

```yaml
features:
  onlineTextEditor:
    valueType: BOOLEAN
    defaultValue: true
usageLimits:
  // highlight-start
  onlineTextEditorConcurrentUsersPreference:
    valueType: TEXT
    defaultValue: Ideal for 1-3 concurrent users
    linkedFeatures:
    - onlineTextEditor
  // highlight-end
plans:
  // highlight-start
  FREE:
  PROFESSIONAL:
    usageLimits:
      onlineTextEditorConcurrentUsersPreference:
        value: Ideal for 5+ concurrent users
  ENTERPRISE:
    usageLimits:
      value: Ideal for 15+ concurrent users
  // highlight-end
```

---
# Frequently asked questions (FAQ)

This section provides some solutions to common errors that occur while working with the Pricing4SaaS suite within a SaaS. For now, there are not known errors in the versions of the libraries supported by this documentation. If you are facing any issues, please refer to either [Pricing4Java](https://github.com/isa-group/Pricing4Java) or [Pricing4React](https://github.com/isa-group/Pricing4React) GitHub repository.

## How do I express an unlimited amount in usage limits?

In yaml you can use the keywork `.inf` of the [YAML specification](https://yaml.org/type/float.html) to express an unlimited amount of something. See Canonical and Examples section to see the usage and the syntax definition.

This keyword is very usefull in Pricing2Yaml specification if you want to model an usage limit that in some tier
of your plan is _Unlimited_.

Example:

```yaml
usageLimits:
  todoNotesLimit:
    valueType: NUMERIC
    defaultValue: 10
plans:
  FREE:
    usageLimits: null
  STANDARD:
    usageLimits:
      todoNotesLimit: .inf
```