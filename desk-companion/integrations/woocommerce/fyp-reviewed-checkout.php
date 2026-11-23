<?php
/**
 * Plugin Name: FYP Alice reviewed sandbox checkout
 * Description: Bind an approved guest cart to the installed WooCommerce Stripe test gateway.
 */
namespace FYP\ReviewedCheckout;

use Automattic\WooCommerce\StoreApi\Exceptions\RouteException;

defined('ABSPATH') || exit;

function sandbox_ready() {
    return home_url() === 'http://127.0.0.1:8993'
        && get_woocommerce_currency() === 'HKD' && wc_get_price_decimals() === 2
        && function_exists('wc_stripe_test_mode') && wc_stripe_test_mode()
        && str_starts_with(wc_stripe_get_publishable_key(), 'pk_test_');
}

function permission($request) {
    $hash = get_option('fyp_alice_review_hash', '');
    $key = $request->get_header('X-FYP-Review-Key');
    return is_string($key) && $key !== '' && $hash !== '' && hash_equals($hash, hash('sha256', $key))
        && sandbox_ready();
}

function cents($value) {
    return (int) wc_add_number_precision((float) $value);
}

function terms($order, $basket) {
    $lines = array_values($order->get_items());
    $shipping = array_values($order->get_items('shipping'));
    if (!$lines || count($lines) > 8 || count($shipping) > 1 || (!$basket && count($lines) !== 1)) {
        return null;
    }
    $items = [];
    $skus = [];
    foreach ($lines as $line) {
        $product = $line->get_product();
        $variation = $line->get_variation_id();
        $id = $variation ?: $line->get_product_id();
        if (!$product || $product->get_id() !== $id || isset($items[$id])
            || ($variation && (!$basket || $product->get_parent_id() !== $line->get_product_id()
                || in_array('', $product->get_variation_attributes(), true)))) {
            return null;
        }
        $sku = $product->get_sku();
        $quantity = $line->get_quantity();
        if ($sku === '' || isset($skus[strtolower($sku)]) || $quantity < 1 || $quantity > 99) {
            return null;
        }
        $skus[strtolower($sku)] = true;
        $subtotal = cents($line->get_subtotal());
        $items[$id] = [
            'product_id' => $id, 'sku' => $sku, 'quantity' => $quantity,
            'subtotal_minor' => $subtotal, 'discount_minor' => $subtotal - cents($line->get_total()),
            'subtotal_tax_minor' => cents($line->get_subtotal_tax()), 'tax_minor' => cents($line->get_total_tax()),
        ];
    }
    $totals = [
        'currency' => $order->get_currency(),
        'subtotal_minor' => array_sum(array_column($items, 'subtotal_minor')), 'discount_minor' => cents($order->get_discount_total()),
        'shipping_minor' => cents($order->get_shipping_total()), 'tax_minor' => cents($order->get_total_tax()),
        'fees_minor' => cents($order->get_total_fees()), 'total_minor' => cents($order->get_total()),
        'rate_id' => $shipping ? $shipping[0]->get_method_id() . ':' . $shipping[0]->get_instance_id() : '',
    ];
    if (!$basket) {
        return $totals + array_intersect_key(reset($items), array_flip(['product_id', 'sku', 'quantity']));
    }
    $delivery = $shipping[0] ?? null;
    $shipping_tax = cents($order->get_shipping_tax());
    if ($totals['shipping_minor'] !== ($delivery ? cents($delivery->get_total()) : 0)
        || $shipping_tax !== ($delivery ? cents($delivery->get_total_tax()) : 0)) {
        return null;
    }
    ksort($items, SORT_NUMERIC);
    $fees = [];
    foreach ($order->get_items('fee') as $fee) {
        $fees[] = [
            'name' => html_entity_decode($fee->get_name(), ENT_QUOTES | ENT_HTML5, 'UTF-8'),
            'total_minor' => cents($fee->get_total()), 'tax_minor' => cents($fee->get_total_tax()),
        ];
    }
    usort($fees, static fn($a, $b) => strcmp($a['name'], $b['name'])
        ?: ($a['total_minor'] <=> $b['total_minor']) ?: ($a['tax_minor'] <=> $b['tax_minor']));
    return $totals + [
        'items' => array_values($items), 'fees' => $fees, 'shipping_tax_minor' => $shipping_tax,
    ];
}

// SQLite and REST clients can serialize object fields in different orders.
function same_terms($actual, $expected) {
    if (!is_array($actual)) return $actual === $expected;
    if (!is_array($expected) || count($actual) !== count($expected)) return false;
    foreach ($actual as $field => $value) {
        if (!array_key_exists($field, $expected) || !same_terms($value, $expected[$field])) return false;
    }
    return true;
}

// This sandbox has its own acceptance policy. A dispatched or partly refunded
// order needs merchant review. The buyer can only cancel the original FYP guest order.
function can_cancel_order($order) {
    if (!$order->has_status('processing') || !$order->get_date_paid() || $order->get_date_completed()
        || !$order->get_items('shipping') || cents($order->get_total_refunded()) !== 0
        || $order->get_meta('_wc_shipment_tracking_items')) {
        return false;
    }
    if (\Automattic\WooCommerce\Utilities\FeaturesUtil::feature_is_enabled('fulfillments')) {
        $store = wc_get_container()->get(\Automattic\WooCommerce\Admin\Features\Fulfillments\DataStore\FulfillmentsDataStore::class);
        foreach ($store->read_fulfillments('order', (string) $order->get_id()) as $fulfillment) {
            if ($fulfillment->get_is_fulfilled()) return false;
        }
    }
    return true;
}

function receipt($ref) {
    $id = (int) get_option('fyp_alice_order_' . $ref, 0);
    if (!$id) {
        return ['found' => false];
    }
    $order = wc_get_order($id);
    if (!$order || $order->get_meta('_fyp_alice_reference') !== $ref) {
        return new \WP_Error('fyp_unverified', 'Order association unavailable.', ['status' => 409]);
    }
    return [
        'found' => true, 'test_mode' => sandbox_ready(), 'order_id' => $order->get_id(),
        'paid' => $order->is_paid() && (bool) $order->get_date_paid(),
        'status' => $order->get_status(),
        'buyer_cancel_requested' => (bool) $order->get_meta('_fyp_buyer_cancel'),
        'can_cancel' => can_cancel_order($order),
        'refunded_minor' => cents($order->get_total_refunded()), 'gateway' => $order->get_payment_method(),
        'guest' => $order->get_customer_id() === 0, 'terms' => terms($order, (bool) $order->get_meta('_fyp_alice_basket')),
        'intent' => $order->get_meta('_payment_intent_id'), 'transaction' => $order->get_transaction_id(),
    ];
}

function checkout($request) {
    global $wpdb;
    $ref = $request['ref'];
    $approved = $request->get_json_params()['approved'] ?? [];
    $cart_basis = $request->get_json_params()['cart_basis'] ?? $approved;
    $payment_method = $request->get_json_params()['test_method'] ?? '';
    $cart = $request->get_header('Cart-Token');
    if (!is_array($approved) || !is_array($cart_basis) || !is_string($payment_method) || !preg_match('/^pm_[a-zA-Z0-9]+$/D', $payment_method)
        || !$cart || ($approved['currency'] ?? '') !== 'HKD' || (int) ($approved['total_minor'] ?? 0) < 1) {
        return new \WP_Error('fyp_invalid', 'Incomplete cart approval.', ['status' => 400]);
    }
    // Serialise the same local review across requests and PHP workers. The order mapping
    // is saved before the gateway, so a lost response can only reopen that order.
    $lock = 'fyp_alice_' . $ref;
    if ('1' !== (string) $wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 3)', $lock))) {
        return new \WP_Error('fyp_busy', 'Checkout already in progress.', ['status' => 409]);
    }
    $revision = null;
    $basket = array_key_exists('items', $approved);
    $guard = static function ($order, $at_gateway = false) use ($approved, $cart_basis, $basket, &$revision) {
        if (!sandbox_ready() || $order->get_payment_method() !== 'stripe_cc' || $order->get_customer_id() !== 0) {
            throw new RouteException('fyp_test_mode_required', 'Test guest checkout is required.', 409);
        }
        $actual = terms($order, $basket);
        if (same_terms($actual, $approved)) {
            return;
        }
        // A previously observed checkout-only adjustment can be applied after draft creation.
        // Only its original cart may reach that step. The gateway requires the exact approved order.
        if (!$at_gateway && $actual && $actual['total_minor'] > 0 && same_terms($actual, $cart_basis)) {
            return;
        }
        $revision = ['terms' => $actual, 'shipping_name' => $order->get_shipping_method()];
        throw new RouteException('fyp_quote_changed', 'The cart changed.', 409);
    };
    $before_payment = static function ($context) use ($guard, $ref, $basket) {
        $order = $context->order;
        $guard($order, true);
        if ($context->payment_method !== 'stripe_cc') {
            throw new RouteException('fyp_test_mode_required', 'Incorrect test gateway.', 409);
        }
        $order->update_meta_data('_fyp_alice_reference', $ref);
        if ($basket) $order->update_meta_data('_fyp_alice_basket', 1);
        $order->save_meta_data();
        if (!add_option('fyp_alice_order_' . $ref, $order->get_id(), '', false)) {
            throw new RouteException('fyp_busy', 'The review already has an order.', 409);
        }
    };
    try {
        $prior = receipt($ref);
        if (is_wp_error($prior) || $prior['found']) {
            return $prior;
        }
        $address = ['first_name'=>'FYP','last_name'=>'Sandbox','address_1'=>'12 Example Road',
                    'city'=>'Hong Kong','state'=>'HONG KONG','postcode'=>'','country'=>'HK'];
        $inner = new \WP_REST_Request('POST', '/wc/store/v1/checkout');
        $inner->set_header('Content-Type', 'application/json');
        $inner->set_header('Cart-Token', $cart);
        $inner->set_body(wp_json_encode([
            'billing_address'=>$address + ['email'=>'fyp-woo@example.com','phone'=>'+12025550142'],
            'shipping_address'=>$address, 'create_account'=>false, 'expected_total'=>(string) max((int) $approved['total_minor'], (int) ($cart_basis['total_minor'] ?? 0)),
            'payment_method'=>'stripe_cc','payment_data'=>[
                ['key'=>'payment_method','value'=>'stripe_cc'],
                ['key'=>'stripe_cc_payment_method_id','value'=>$payment_method],
            ],
        ]));
        // The synthetic checkout must not notify real mail recipients.
        add_filter('pre_wp_mail', '__return_true', PHP_INT_MAX);
        add_action('woocommerce_store_api_checkout_order_processed', $guard, PHP_INT_MAX);
        add_action('woocommerce_rest_checkout_process_payment_with_context', $before_payment, -PHP_INT_MAX);
        $result = rest_do_request($inner);
        if ($result->is_error()) {
            $code = $result->as_error()->get_error_code();
            // The Store API wraps exceptions thrown at payment dispatch. Preserve the
            // decision made by our exact-price guard before it calls the gateway.
            $changed = $revision !== null || in_array($code, ['woocommerce_rest_checkout_total_mismatch','fyp_quote_changed'], true);
            return new \WP_Error($changed ? 'fyp_quote_changed' : 'fyp_checkout_unconfirmed',
                $changed ? 'Review the new cart.' : 'Read the order before another attempt.', ['status'=>409, 'revision'=>$revision]);
        }
        return receipt($ref);
    } finally {
        remove_filter('pre_wp_mail', '__return_true', PHP_INT_MAX);
        remove_action('woocommerce_rest_checkout_process_payment_with_context', $before_payment, -PHP_INT_MAX);
        remove_action('woocommerce_store_api_checkout_order_processed', $guard, PHP_INT_MAX);
        $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)', $lock));
    }
}

function cancel_paid_order($request) {
    global $wpdb;
    $ref = $request['ref'];
    $expected = $request->get_json_params();
    $lock = 'fyp_alice_' . $ref;
    if ('1' !== (string) $wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 3)', $lock))) {
        return new \WP_Error('fyp_busy', 'Read the original order again.', ['status'=>409]);
    }
    try {
        $prior = receipt($ref);
        if (is_wp_error($prior)) return $prior;
        if (!$prior['found'] || !$prior['guest'] || $prior['gateway'] !== 'stripe_cc'
            || !is_array($prior['terms']) || !is_array($expected) || ($expected['order'] ?? null) !== $prior['order_id']
            || ($expected['amount_minor'] ?? null) !== $prior['terms']['total_minor']
            || $prior['terms']['currency'] !== 'HKD') {
            return new \WP_Error('fyp_order_mismatch', 'The reviewed test order does not match.', ['status'=>409]);
        }
        if ($prior['buyer_cancel_requested']) return $prior;
        if (!$prior['can_cancel']) {
            return new \WP_Error('fyp_cancel_unavailable', 'This order cannot be cancelled before dispatch.', ['status'=>409]);
        }
        $order = wc_get_order($prior['order_id']);
        // Record the buyer's request before the gateway call. Retries can only
        // read its outcome, including after a connection or worker failure.
        $order->update_meta_data('_fyp_buyer_cancel', 'yes');
        add_filter('pre_wp_mail', '__return_true', PHP_INT_MAX);
        $order->set_status('on-hold', 'FYP test buyer requested cancellation before dispatch.');
        $order->save();
        $items = [];
        foreach ($order->get_items(['line_item','shipping','fee']) as $id => $item) {
            $items[$id] = [
                'qty' => $item instanceof \WC_Order_Item_Product ? $item->get_quantity() : 0,
                'refund_total' => $item->get_total(),
                'refund_tax' => $item->get_taxes()['total'] ?? [],
            ];
        }
        $refund = wc_create_refund([
            'order_id' => $order->get_id(), 'amount' => $order->get_total(),
            'reason' => 'FYP sandbox buyer cancellation before dispatch', 'refund_payment' => true,
            'restock_items' => true, 'line_items' => $items,
        ]);
        if (is_wp_error($refund)) {
            return new \WP_Error('fyp_refund_unconfirmed', 'Read the original order and payment.', ['status'=>409]);
        }
        return receipt($ref);
    } finally {
        remove_filter('pre_wp_mail', '__return_true', PHP_INT_MAX);
        $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)', $lock));
    }
}

add_action('rest_api_init', static function () {
    $auth = __NAMESPACE__ . '\\permission';
    register_rest_route('fyp-alice/v1', '/orders/(?P<ref>[a-f0-9]{32})/cancel',
        ['methods'=>'POST','permission_callback'=>$auth,'callback'=>__NAMESPACE__ . '\\cancel_paid_order']);
    register_rest_route('fyp-alice/v1', '/store', ['methods'=>'GET','permission_callback'=>$auth,
        'callback'=>static fn() => ['test_mode'=>true,'gateway'=>'stripe_cc','currency'=>'HKD',
            'publishable_fingerprint'=>hash('sha256', wc_stripe_get_publishable_key())]]);
    register_rest_route('fyp-alice/v1', '/orders/(?P<ref>[a-f0-9]{32})', [
        ['methods'=>'GET','permission_callback'=>$auth,'callback'=>static fn($request)=>receipt($request['ref'])],
        ['methods'=>'POST','permission_callback'=>$auth,'callback'=>__NAMESPACE__ . '\\checkout'],
    ]);
});
