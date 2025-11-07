package org.isa.pricing.csp.output;

import java.util.Set;

import lombok.Data;

@Data
public class ConfigurationSpace {
    private Set<SubscriptionItem> subscriptions;
    public Integer getCardinality() {
        return subscriptions != null ? subscriptions.size() : 0;
    }
}
