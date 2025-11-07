package org.isa.pricing.csp.output;

import lombok.Data;

@Data
public class SubscriptionItem {
    private Subscription subscription;
    private String cost;
}
