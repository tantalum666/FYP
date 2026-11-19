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

function terms($order) {
    $lines = array_values($order->get_items());
    $shipping = array_values($order->get_items('shipping'));
    if (count($lines) !== 1 || count($shipping) > 1 || !$lines[0]->get_product()) {
        return null;
    }
    $line = $lines[0];
    return [
        'product_id' => $line->get_product_id(), 'sku' => $line->get_product()->get_sku(),
        'quantity' => $line->get_quantity(), 'currency' => $order->get_currency(),
        'subtotal_minor' => cents($line->get_subtotal()), 'discount_minor' => cents($order->get_discount_total()),
        'shipping_minor' => cents($order->get_shipping_total()), 'tax_minor' => cents($order->get_total_tax()),
        'fees_minor' => cents($order->get_total_fees()), 'total_minor' => cents($order->get_total()),
        'rate_id' => $shipping ? $shipping[0]->get_method_id() . ':' . $shipping[0]->get_instance_id() : '',
    ];
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
        'status' => $order->get_status(), 'gateway' => $order->get_payment_method(),
        'guest' => $order->get_customer_id() === 0, 'terms' => terms($order),
        'intent' => $order->get_meta('_payment_intent_id'), 'transaction' => $order->get_transaction_id(),
    ];
}

function checkout($request) {
    global $wpdb;
    $ref = $request['ref'];
    $approved = $request->get_json_params()['approved'] ?? [];
    $payment_method = $request->get_json_params()['test_method'] ?? '';
    $cart = $request->get_header('Cart-Token');
    if (!is_array($approved) || !is_string($payment_method) || !preg_match('/^pm_[a-zA-Z0-9]+$/D', $payment_method)
        || !$cart || ($approved['currency'] ?? '') !== 'HKD' || (int) ($approved['total_minor'] ?? 0) < 1) {
        return new \WP_Error('fyp_invalid', 'Incomplete cart approval.', ['status' => 400]);
    }
    // Serialise the same local review across requests and PHP workers. The order mapping
    // is saved before the gateway, so a lost response can only reopen that order.
    $lock = 'fyp_alice_' . $ref;
    if ('1' !== (string) $wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 3)', $lock))) {
        return new \WP_Error('fyp_busy', 'Checkout already in progress.', ['status' => 409]);
    }
    $guard = static function ($order) use ($approved) {
        $actual = terms($order);
        if (!sandbox_ready() || $order->get_payment_method() !== 'stripe_cc' || $order->get_customer_id() !== 0) {
            throw new RouteException('fyp_test_mode_required', 'Test guest checkout is required.', 409);
        }
        if ($actual === null || count($approved) !== count($actual)) {
            throw new RouteException('fyp_quote_changed', 'The cart changed.', 409);
        }
        foreach ($actual as $field => $value) {
            if (!array_key_exists($field, $approved) || $approved[$field] !== $value) {
                throw new RouteException('fyp_quote_changed', 'The cart changed.', 409);
            }
        }
    };
    $before_payment = static function ($context) use ($guard, $ref) {
        $order = $context->order;
        $guard($order);
        if ($context->payment_method !== 'stripe_cc') {
            throw new RouteException('fyp_test_mode_required', 'Incorrect test gateway.', 409);
        }
        $order->update_meta_data('_fyp_alice_reference', $ref);
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
            'shipping_address'=>$address, 'create_account'=>false, 'expected_total'=>(string) $approved['total_minor'],
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
            $changed = in_array($code, ['woocommerce_rest_checkout_total_mismatch','fyp_quote_changed'], true);
            return new \WP_Error($changed ? 'fyp_quote_changed' : 'fyp_checkout_unconfirmed',
                $changed ? 'Review the new cart.' : 'Read the order before another attempt.', ['status'=>409]);
        }
        return receipt($ref);
    } finally {
        remove_filter('pre_wp_mail', '__return_true', PHP_INT_MAX);
        remove_action('woocommerce_rest_checkout_process_payment_with_context', $before_payment, -PHP_INT_MAX);
        remove_action('woocommerce_store_api_checkout_order_processed', $guard, PHP_INT_MAX);
        $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)', $lock));
    }
}

add_action('rest_api_init', static function () {
    $auth = __NAMESPACE__ . '\\permission';
    register_rest_route('fyp-alice/v1', '/store', ['methods'=>'GET','permission_callback'=>$auth,
        'callback'=>static fn() => ['test_mode'=>true,'gateway'=>'stripe_cc','currency'=>'HKD',
            'publishable_fingerprint'=>hash('sha256', wc_stripe_get_publishable_key())]]);
    register_rest_route('fyp-alice/v1', '/orders/(?P<ref>[a-f0-9]{32})', [
        ['methods'=>'GET','permission_callback'=>$auth,'callback'=>static fn($request)=>receipt($request['ref'])],
        ['methods'=>'POST','permission_callback'=>$auth,'callback'=>__NAMESPACE__ . '\\checkout'],
    ]);
});
