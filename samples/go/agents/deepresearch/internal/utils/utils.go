// Package utils provides small generic helpers.
package utils

import (
	"encoding/json"
	"fmt"
)

// Must returns v if err is nil, otherwise panics.
func Must[T any](v T, err error) T {
	if err != nil {
		panic(err.Error())
	}
	return v
}

// PrettyPrint is a debug printing utility.
func PrettyPrint(v any) {
	b, err := json.MarshalIndent(v, "", " ")
	if err != nil {
		fmt.Printf("failed to marshal %T: %v\n", v, err)
	} else {
		fmt.Println(string(b))
	}
}

// ToMapStruct uses json codec round-trip to represent struct as a map.
func ToMapStruct(v any) (map[string]any, error) {
	b, err := json.Marshal(v)
	if err != nil {
		return nil, fmt.Errorf("ToMapStruct: marshal %T: %w", v, err)
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, fmt.Errorf("ToMapStruct: unmarshal %T: %w", v, err)
	}
	return m, nil
}

// FromMapStruct uses json codec round-trip to represent map as a struct.
func FromMapStruct[T any](v map[string]any) (T, error) {
	var out T
	b, err := json.Marshal(v)
	if err != nil {
		return out, fmt.Errorf("FromMapStruct: marshal map: %w", err)
	}
	if err := json.Unmarshal(b, &out); err != nil {
		return out, fmt.Errorf("FromMapStruct: unmarshal into %T: %w", out, err)
	}
	return out, nil
}
