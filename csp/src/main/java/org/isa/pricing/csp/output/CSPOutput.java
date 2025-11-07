package org.isa.pricing.csp.output;

import java.util.List;
import java.util.Map;

import lombok.Data;

@Data
public class CSPOutput {
    private MessageType messageType;
    private ConfigurationSpace configurationSpace;
    private List<String> errors;
    private String model;
    private Map<String, Object> variables;
}
