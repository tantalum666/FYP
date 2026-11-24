<?php
// Exercise the production merchant terms with in-memory Woo order records.
define('ABSPATH', __DIR__);
function add_action(...$args) {}
function wc_add_number_precision($value) { return round($value * 100); }
require __DIR__ . '/../../integrations/woocommerce/fyp-reviewed-checkout.php';

class WooRecord {
    public function __construct(public array $fields) {}
    public function __call($method, $args) {
        return $this->fields[substr($method, 4)];
    }
    public function get_items($kind = 'line_item') {
        return $this->fields['items'][$kind] ?? [];
    }
}
function line($id, $sku, $quantity, $subtotal, $parent = 0) {
    $product = new WooRecord(['id' => $id, 'sku' => $sku, 'parent_id' => $parent,
        'variation_attributes' => ['attribute_color' => 'blue']]);
    return new WooRecord(['product' => $product, 'variation_id' => $parent ? $id : 0,
        'product_id' => $parent ?: $id, 'quantity' => $quantity, 'subtotal' => $subtotal,
        'total' => $subtotal, 'subtotal_tax' => 0, 'total_tax' => 0]);
}
$tissues = line(21, 'FYP-QA-POCKET-TISSUES', 2, 8);
$pen = line(43, 'FYP-QA-PEN-BLUE', 1, 17, 42);
$delivery = new WooRecord(['method_id' => 'flat_rate', 'instance_id' => 1, 'total' => 8, 'total_tax' => 0]);
$order = new WooRecord([
    'items' => ['line_item' => [$pen, $tissues], 'shipping' => [$delivery]],
    'currency' => 'HKD', 'discount_total' => 0, 'shipping_total' => 8, 'shipping_tax' => 0,
    'total_tax' => 0, 'total_fees' => 0, 'total' => 33,
]);
$approved = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
$read = \FYP\ReviewedCheckout\terms($order, true);
$matches = \FYP\ReviewedCheckout\same_terms($read, $approved);
$inconsistent_shipping = [];
foreach (['total' => 7.99, 'total_tax' => 0.01] as $field => $changed) {
    $before = $delivery->fields[$field];
    $delivery->fields[$field] = $changed;
    $inconsistent_shipping[] = \FYP\ReviewedCheckout\terms($order, true);
    $delivery->fields[$field] = $before;
}
$pen->fields['product'] = new WooRecord(['id' => 44, 'sku' => 'FYP-QA-PEN-RED', 'parent_id' => 42,
    'variation_attributes' => ['attribute_color' => 'red']]);
$pen->fields['variation_id'] = 44;
$substituted = \FYP\ReviewedCheckout\same_terms(\FYP\ReviewedCheckout\terms($order, true), $approved);
$order->fields['items']['line_item'] = [line(15, 'FYP-QA-DELIVERY-PACK', 2, 34)];
$order->fields['total'] = 42;
$first_refund = new WooRecord(['parent_id' => 67, 'currency' => 'HKD', 'amount' => 7]);
$second_refund = new WooRecord(['parent_id' => 67, 'currency' => 'HKD', 'amount' => 8]);
$order->fields += ['id' => 67, 'refunds' => [$first_refund, $second_refund], 'total_refunded' => 15];
$refund_totals = [\FYP\ReviewedCheckout\refunded_minor($order)];
foreach (['parent_id' => 68, 'currency' => 'USD', 'amount' => 12] as $field => $changed) {
    $before = $second_refund->fields[$field];
    $second_refund->fields[$field] = $changed;
    $refund_totals[] = \FYP\ReviewedCheckout\refunded_minor($order);
    $second_refund->fields[$field] = $before;
}
echo json_encode(['basket' => $read, 'matches' => $matches, 'inconsistent_shipping' => $inconsistent_shipping, 'substituted' => $substituted,
    'legacy' => \FYP\ReviewedCheckout\terms($order, false), 'refund_totals' => $refund_totals], JSON_THROW_ON_ERROR);
