a2ui 0.2
You are designing a JSON schema which represents a UI, composed of a hierarchy of components, which reference each other via ID.There is a root component, a list of components, a globals style, and a shared data model for the components.
Write a JSON schema to fullfill these requirements, considering the following:
- Include description fields throughout the JSON to explain what it 

## Supported ComponentTypes
The following is the set of supported widgets, along with key properties in them.The properties are not exhaustive, just some ideas
    - Text: Text, supporting markdown
        - text
        - List: For positioning items in a linear fashion
            - direction - vertical / horizontal
            - children - list of ComponentInstanceRefs
                - distribution - start / center / end on the main axis
                    - alignment - start / center / end on the cross axis
                        - Card: For displaying related items within a visual container
                            - child: ComponentRef
                                - Image:
- fit: hint for how to fit the image to the space, e.g.cover, contain, etc
    - max_width
    - max_height
    - aspect_ratio
    - url
    - Video:
- max_width
    - max_height
    - aspect_ratio
    - url
    - AudioPlayer
    - description
    - url
    - CheckBox
    - TextField
    - description
    - type - shortText / number / date / longText
    - MutuallyExclusiveMultipleChoice e.g.radio buttons
        - options - list of string
            - MultipleChoice e.g.check boxes
                - options - list of string
                    - Button
                    - label
                    - action
                    - Slider
                    - min_value
                    - max_value
                    - Tabs
                    - Divider
                    - Carousel
## Concepts
ComponentType - a type of component that is supported e.g.List, CheckBoxes

Component - A specific instance of a ComponentType.Each Component has a unique id, a type, and the necessary data for that type, using an 'any' construct.
    Layout - A renderable layout which contains a hierarchy of
ComponentInstanceRef - an ID type which is a reference to a component instance
ComponentInstanceListRef - reference to a list of components.This can be be * either * an explicit list of ComponentInstanceRefs * or * a template Component and a DataBinding reference to a list of data, where the template can refer to local paths within specific data items in the list.
    Style - a very basic style type which affects a set of Components
        - primary_color
        - agent_logo
DataBinding - some data to include in the UI, which can be * any * of
    - A reference to the global data model, starting with a leading "/"
        - A reference to a local data model item, starting without a leading "/"
            - A literal value
Action - an action that can be handled, e.g.a button click or
    - label - name of action
DataModel - an arbitrary JSON data structure which the UI can refer to

## Prior art
There are some other format that we will try to borrow concepts from.Consider these and try to integrate them into the design as closely as possible.

    Schema:

{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.com/ui-layout.schema.json",
            "title": "UI Layout",
                "description": "A schema for defining a UI layout composed of a hierarchy of components, a global style, and a shared data model.",
                    "type": "object",
                        "properties": {
        "root": {
            "$ref": "#/$defs/componentInstanceRef",
                "description": "The ID of the root component from which rendering should begin."
        },
        "components": {
            "type": "array",
                "description": "A flat list of all component instances available for rendering. Components reference each other by ID.",
                    "items": {
                "$ref": "#/$defs/component"
            }
        },
        "globals": {
            "$ref": "#/$defs/style",
                "description": "Global style definitions that can be applied to the entire UI."
        },
        "dataModel": {
            "$ref": "#/$defs/dataModel",
                "description": "An arbitrary JSON object representing the data available to the UI components."
        }
    },
    "required": [
        "root",
        "components"
    ],
        "$defs": {
        "componentInstanceRef": {
            "description": "A reference to a component instance by its unique ID.",
                "type": "string"
        },
        "componentInstanceListRef": {
            "description": "A reference to a list of components. Can be an explicit list of IDs or a template with a data binding to a list in the data model.",
                "oneOf": [
                    {
                        "description": "An explicit list of component instance IDs.",
                        "type": "array",
                        "items": {
                            "$ref": "#/$defs/componentInstanceRef"
                        }
                    },
                    {
                        "description": "A template to be rendered for each item in a data-bound list.",
                        "type": "object",
                        "properties": {
                            "template": {
                                "$ref": "#/$defs/componentInstanceRef"
                            },
                            "dataBinding": {
                                "$ref": "#/$defs/dataBinding",
                                "description": "A data binding reference to a list within the data model."
                            }
                        },
                        "required": [
                            "template",
                            "dataBinding"
                        ]
                    }
                ]
        },
        "style": {
            "description": "Defines global styling properties for the UI.",
                "type": "object",
                    "properties": {
                "primary_color": {
                    "type": "string",
                        "description": "The primary color for the UI, in hex format (e.g., '#RRGGBB').",
                            "pattern": "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
                },
                "agent_logo": {
                    "type": "string",
                        "description": "URL of an agent logo to be displayed.",
                            "format": "uri"
                }
            }
        },
        "dataBinding": {
            "description": "A value that can be a literal, a reference to the global data model (starts with '/'), or a reference to a local data context (does not start with '/').",
                "oneOf": [
                    {
                        "type": "string",
                        "description": "A string path to data in the model."
                    },
                    {
                        "type": "number",
                        "description": "A literal number value."
                    },
                    {
                        "type": "boolean",
                        "description": "A literal boolean value."
                    },
                    {
                        "type": "object",
                        "description": "A literal JSON object."
                    },
                    {
                        "type": "array",
                        "description": "A literal JSON array."
                    }
                ]
        },
        "action": {
            "description": "Represents a user-initiated action, like a button click, which can carry both static and dynamically-resolved contextual data.",
                "type": "object",
                    "properties": {
                "action": {
                    "type": "string",
                        "description": "A unique name identifying the action to be handled by the application logic (e.g., 'submitForm', 'generateDog')."
                },
                "staticContext": {
                    "type": "object",
                        "description": "A plain JSON object of static, literal values to be passed along with the action. This data is fixed and does not change."
                },
                "dynamicContext": {
                    "type": "object",
                        "description": "A key-value map where each value is a data binding. These bindings are resolved to their current values from the UI state or data model at the exact moment the action is triggered.",
                            "additionalProperties": {
                        "$ref": "#/$defs/dataBinding"
                    }
                }
            },
            "required": [
                "action"
            ]
        },
        "dataModel": {
            "description": "An arbitrary JSON data structure that the UI can refer to for dynamic content.",
                "type": "object"
        },
        "componentType": {
            "description": "The set of supported component types.",
                "enum": [
                    "Text",
                    "List",
                    "Card",
                    "Image",
                    "AudioPlayer",
                    "TextField",
                    "MutuallyExclusiveMultipleChoice",
                    "MultipleChoice",
                    "Button",
                    "Slider",
                    "Tabs",
                    "Divider",
                    "Carousel"
                ]
        },
        "component": {
            "description": "A specific instance of a ComponentType with its own unique ID and properties. The properties are validated based on the 'type' field.",
                "type": "object",
                    "properties": {
                "id": {
                    "type": "string",
                        "description": "A unique identifier for this component instance."
                },
                "type": {
                    "$ref": "#/$defs/componentType"
                }
            },
            "required": [
                "id",
                "type"
            ],
                "oneOf": [
                    {
                        "properties": {
                            "type": { "const": "Text" },
                            "text": { "type": "string", "description": "The text content to display, supporting markdown." }
                        },
                        "required": ["text"]
                    },
                    {
                        "properties": {
                            "type": { "const": "List" },
                            "direction": { "enum": ["vertical", "horizontal"], "default": "vertical" },
                            "children": { "$ref": "#/$defs/componentInstanceListRef" },
                            "distribution": { "enum": ["start", "center", "end"], "description": "Distribution of items along the main axis." },
                            "alignment": { "enum": ["start", "center", "end"], "description": "Alignment of items along the cross axis." }
                        },
                        "required": ["children"]
                    },
                    {
                        "properties": {
                            "type": { "const": "Card" },
                            "child": { "$ref": "#/$defs/componentInstanceRef" }
                        },
                        "required": ["child"]
                    },
                    {
                        "properties": {
                            "type": { "const": "Image" },
                            "url": { "type": "string", "format": "uri" },
                            "fit": { "type": "string", "description": "Hint for how to fit the image to its container (e.g., 'cover', 'contain')." },
                            "max_width": { "type": "number" },
                            "max_height": { "type": "number" }
                        },
                        "required": ["url"]
                    },
                    {
                        "properties": {
                            "type": { "const": "AudioPlayer" },
                            "url": { "type": "string", "format": "uri" },
                            "description": { "type": "string", "description": "A description or title for the audio clip." }
                        },
                        "required": ["url"]
                    },
                    {
                        "properties": {
                            "type": { "const": "TextField" },
                            "description": { "type": "string", "description": "A label or placeholder text for the input field." },
                            "inputType": { "enum": ["shortText", "number", "date", "longText"], "description": "The type of data expected in the text field." },
                            "valueBinding": {
                                "$ref": "#/$defs/dataBinding",
                                "description": "A data binding to a key in the data model that this field's value is synced with."
                            }
                        }
                    },
                    {
                        "properties": {
                            "type": { "const": "MutuallyExclusiveMultipleChoice" },
                            "options": { "type": "array", "items": { "type": "string" }, "description": "A list of options where only one can be selected." },
                            "valueBinding": {
                                "$ref": "#/$defs/dataBinding",
                                "description": "A data binding to a key in the data model that the selected option is synced with."
                            }
                        },
                        "required": ["options"]
                    },
                    {
                        "properties": {
                            "type": { "const": "MultipleChoice" },
                            "options": { "type": "array", "items": { "type": "string" }, "description": "A list of options where multiple can be selected." },
                            "valueBinding": {
                                "$ref": "#/$defs/dataBinding",
                                "description": "A data binding to a key in the data model that the array of selected options is synced with."
                            }
                        },
                        "required": ["options"]
                    },
                    {
                        "properties": {
                            "type": { "const": "Button" },
                            "label": { "type": "string" },
                            "action": { "$ref": "#/$defs/action" }
                        },
                        "required": ["label", "action"]
                    },
                    {
                        "properties": {
                            "type": { "const": "Slider" },
                            "min": { "type": "number", "default": 0 },
                            "max": { "type": "number", "default": 100 },
                            "step": { "type": "number", "default": 1 },
                            "valueBinding": {
                                "$ref": "#/$defs/dataBinding",
                                "description": "A data binding to a key in the data model that this slider's numeric value is synced with."
                            }
                        }
                    },
                    {
                        "properties": {
                            "type": { "const": "Tabs" },
                            "tabItems": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": { "label": { "type": "string" }, "child": { "$ref": "#/$defs/componentInstanceRef" } },
                                    "required": ["label", "child"]
                                }
                            }
                        },
                        "required": ["tabItems"]
                    },
                    {
                        "properties": {
                            "type": { "const": "Divider" }
                        }
                    },
                    {
                        "properties": {
                            "type": { "const": "Carousel" },
                            "children": { "$ref": "#/$defs/componentInstanceListRef" }
                        },
                        "required": ["children"]
                    }
                ]
        }
    }
}

Example data item prompt:
Generate a JSON conforming to the schema to describe the following UI:
A vertical list containing a search form and a list of results for a restaurant finder.

The search form is a card containing:
- A title: "Restaurant Finder"
    - A text input for "Cuisine"
        - A multiple choice for "Price Range"
            - A button labeled "Search"

Below the form is a list of restaurant results, which are rendered from a list in the data model at`/restaurants`.Each result is a card showing:
- The restaurant's image
    - The restaurant's name
        - The restaurant's rating

Example data item
{
    "root": "root-list",
        "dataModel": {
        "restaurants": [
            {
                "name": "The Gourmet Kitchen",
                "rating": "4.5/5",
                "imageUrl": "https://placehold.co/600x400/F7B32B/FFFFFF?text=Gourmet+Kitchen"
            },
            {
                "name": "Pasta Palace",
                "rating": "4.2/5",
                "imageUrl": "https://placehold.co/600x400/2D3A3A/FFFFFF?text=Pasta+Palace"
            },
            {
                "name": "Sushi Central",
                "rating": "4.8/5",
                "imageUrl": "https://placehold.co/600x400/A2A2A2/FFFFFF?text=Sushi+Central"
            }
        ],
            "formInput": {
            "cuisine": "Italian",
                "price": []
        }
    },
    "components": [
        {
            "id": "root-list",
            "type": "List",
            "direction": "vertical",
            "children": [
                "search-form-card",
                "results-divider",
                "results-list"
            ]
        },
        {
            "id": "search-form-card",
            "type": "Card",
            "child": "search-form"
        },
        {
            "id": "search-form",
            "type": "List",
            "direction": "vertical",
            "children": [
                "search-title",
                "cuisine-input",
                "price-input",
                "search-button"
            ]
        },
        {
            "id": "search-title",
            "type": "Text",
            "text": "## Restaurant Finder"
        },
        {
            "id": "cuisine-input",
            "type": "TextField",
            "description": "Cuisine (e.g., Italian, Mexican)",
            "inputType": "shortText",
            "valueBinding": "/formInput/cuisine"
        },
        {
            "id": "price-input",
            "type": "MultipleChoice",
            "description": "Price Range",
            "options": ["$", "$$", "$$$", "$$$$"],
            "valueBinding": "/formInput/price"
        },
        {
            "id": "search-button",
            "type": "Button",
            "label": "Search",
            "action": {
                "action": "findRestaurants",
                "dynamicContext": {
                    "cuisine": "/formInput/cuisine",
                    "price": "/formInput/price"
                }
            }
        },
        {
            "id": "results-divider",
            "type": "Divider"
        },
        {
            "id": "results-list",
            "type": "List",
            "direction": "vertical",
            "children": {
                "template": "restaurant-item-card",
                "dataBinding": "/restaurants"
            }
        },
        {
            "id": "restaurant-item-card",
            "type": "Card",
            "child": "restaurant-item-content"
        },
        {
            "id": "restaurant-item-content",
            "type": "List",
            "direction": "horizontal",
            "alignment": "center",
            "children": [
                "restaurant-item-image",
                "restaurant-item-details"
            ]
        },
        {
            "id": "restaurant-item-image",
            "type": "Image",
            "url": {
                "dataBinding": "imageUrl"
            },
            "max_width": 100,
            "max_height": 100,
            "fit": "cover"
        },
        {
            "id": "restaurant-item-details",
            "type": "List",
            "direction": "vertical",
            "children": [
                "restaurant-item-name",
                "restaurant-item-rating"
            ]
        },
        {
            "id": "restaurant-item-name",
            "type": "Text",
            "text": {
                "dataBinding": "name"
            }
        },
        {
            "id": "restaurant-item-rating",
            "type": "Text",
            "text": {
                "dataBinding": "rating"
            }
        }
    ]
}
