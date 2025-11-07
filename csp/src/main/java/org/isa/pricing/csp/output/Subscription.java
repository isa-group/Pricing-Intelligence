package org.isa.pricing.csp.output;

import java.util.List;
import java.util.Map;

import lombok.Data;

@Data
public class Subscription {
    private String plan;
    private List<String> addOns;
    private List<String> features;
    private List<Map<String, Double>> usageLimits;
}
